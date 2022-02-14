from odoo import http
from odoo.http import request

from babel.dates import format_datetime, format_date
from datetime import datetime
from dateutil.relativedelta import relativedelta
import json
import pytz
from odoo.addons.appointment.controllers.main import Appointment
from odoo.addons.website_sale.controllers.main import WebsiteSale
from werkzeug.exceptions import NotFound
from werkzeug.urls import url_encode

from odoo import http, _, fields
from odoo.http import request
from odoo.osv import expression
from odoo.tools import html2plaintext, is_html_empty, plaintext2html, DEFAULT_SERVER_DATETIME_FORMAT as dtf
from odoo.tools.misc import get_lang

from odoo.addons.base.models.ir_ui_view import keep_query
from odoo.addons.http_routing.models.ir_http import slug

class Appointment_Extend(Appointment):
    @http.route('/appointment_payments',type="http",auth="user",website=True)
    def customer_form(self,**kw):
        return http.request.render('custom_appointment.appointment_payment')

    @http.route(['/calendar/<model("calendar.appointment.type"):appointment_type>/submit'], type='http', auth="public",
                website=True, methods=["POST"])
    def calendar_appointment_submit(self, appointment_type, datetime_str, duration_str, employee_id, name, phone, email,
                                    **kwargs):
        """
        Create the event for the appointment and redirect on the validation page with a summary of the appointment.

        :param appointment_type: the appointment type related
        :param datetime_str: the string representing the datetime
        :param employee_id: the employee selected for the appointment
        :param name: the name of the user sets in the form
        :param phone: the phone of the user sets in the form
        :param email: the email of the user sets in the form
        """
        send_again={}



        timezone = request.session['timezone'] or appointment_type.appointment_tz
        tz_session = pytz.timezone(timezone)
        date_start = tz_session.localize(fields.Datetime.from_string(datetime_str)).astimezone(pytz.utc)
        duration = float(duration_str)
        date_end = date_start + relativedelta(hours=duration)

        send_again['date_start'] = date_start
        send_again['date_end'] = date_end
        send_again['duration'] = duration

        employee = request.env['hr.employee'].sudo().browse(int(employee_id)).exists()
        if employee not in appointment_type.sudo().employee_ids:
            raise NotFound()
        if employee.user_id and employee.user_id.partner_id:
            if not employee.user_id.partner_id.calendar_verify_availability(date_start, date_end):
                return request.redirect('/calendar/%s/appointment?state=failed-employee' % slug(appointment_type))

        send_again['employee']=employee.id

        Partner = self._get_customer_partner() or request.env['res.partner'].sudo().search([('email', '=like', email)],
                                                                                           limit=1)
        if Partner:
            if not Partner.calendar_verify_availability(date_start, date_end):
                return request.redirect('/calendar/%s/appointment?state=failed-partner' % appointment_type.id)
            if not Partner.mobile:
                Partner.write({'mobile': phone})
            if not Partner.email:
                Partner.write({'email': email})
        else:
            Partner = Partner.create({
                'name': name,
                'mobile': Partner._phone_format(phone, country=self._get_customer_country()),
                'email': email,
            })

        send_again['Partner'] = Partner.id


        description_bits = []
        description = ''

        if phone:
            description_bits.append(_('Mobile: %s', phone))
        if email:
            description_bits.append(_('Email: %s', email))

        for question in appointment_type.question_ids:
            key = 'question_' + str(question.id)
            if question.question_type == 'checkbox':
                answers = question.answer_ids.filtered(lambda x: (key + '_answer_' + str(x.id)) in kwargs)
                if answers:
                    description_bits.append('%s: %s' % (question.name, ', '.join(answers.mapped('name'))))
            elif question.question_type == 'text' and kwargs.get(key):
                answers = [line for line in kwargs[key].split('\n') if line.strip()]
                description_bits.append('%s:<br/>%s' % (question.name, plaintext2html(kwargs.get(key).strip())))
            elif kwargs.get(key):
                description_bits.append('%s: %s' % (question.name, kwargs.get(key).strip()))
        if description_bits:
            description = '<ul>' + ''.join(['<li>%s</li>' % bit for bit in description_bits]) + '</ul>'

        send_again['description'] = description
        send_again['appointment_type'] = appointment_type.id
        send_again['name'] = name

        request.session['send_again'] = send_again
        # request.session['appointment_type'] = appointment_type
        partner_get = request.env.user.id
        # Product = request.env['product.product'].sudo().search([('id','=', 29)])

        order = request.env['sale.order'].sudo().create({
            'partner_id': partner_get,
            'partner_shipping_id': partner_get,
            'order_line': [(0, 0, {
                'product_id': request.env['product.product'].sudo().search([('name','=', 'Appointment')]).ids[0],
                'price_unit': appointment_type.price_custom,
            })],
        })
        logged_in = not request.env.user._is_public()
        acquirers = request.env['payment.acquirer'].sudo().search([('state', '!=', 'disabled')])
        tokens = request.env['payment.token'].search(
            [('acquirer_id', 'in', acquirers.ids), ('partner_id', '=', order.partner_id.id)]
        ) if logged_in else request.env['payment.token']
        if order:
            request.session['sale_last_order_id'] = order.id
            request.session['sale_order_id'] = order.id
        fees_by_acquirer = {
            acq_sudo: acq_sudo._compute_fees(
                order.amount_total, order.currency_id, order.partner_id.country_id
            ) for acq_sudo in acquirers.filtered('fees_active')
        }

        show_tokenize_input = logged_in \
                              and not request.env['payment.acquirer'].sudo()._is_tokenization_required(
            sale_order_id=order.id
        )

        value = {
            'website_sale_order': order,
            'errors': [],
            'partner': order.partner_id,
            'order': order,
            'payment_action_id': request.env.ref('payment.action_payment_acquirer').id,
            # Payment form common (checkout and manage) values
            'acquirers': acquirers,
            'tokens': tokens,
            'fees_by_acquirer': fees_by_acquirer,
            'show_tokenize_input': show_tokenize_input,
            'amount': order.amount_total,
            'currency': order.currency_id,
            'partner_id': order.partner_id.id,
            'access_token': order._portal_ensure_token(),
            'transaction_route': f'/shop/payment/transaction/{order.id}',
            'landing_route': '/shop/payment/validate',
        }

        return request.render('custom_appointment.payment_option', value)
        # return request.redirect('/appointment_payments')
        # return request.render("website_sale.payment", {'order': order})

    @http.route('/appointment/confirmation', type='http', auth="public", website=True, sitemap=False)
    def payment_validate(self, **kwargs):
        sale_order_id = request.session.get('sale_last_order_id')
        order = request.env['sale.order'].sudo().search([('id','=', sale_order_id)])
        event_id = request.session.get('event')
        event = request.env['calendar.event'].sudo().browse(event_id)
        event.write({'active': True
                     })
        value = {
            'event':event,
            'order':order,
        }
        return request.render('custom_appointment.appointment_confirm',value)


class WebsiteSale(WebsiteSale):

    def _prepare_calendar_values(self, appointment_type, date_start, date_end, duration, description, name, employee, partner):
        """
        prepares all values needed to create a new calendar.event
        """
        categ_id = request.env.ref('appointment.calendar_event_type_data_online_appointment')
        alarm_ids = appointment_type.reminder_ids and [(6, 0, appointment_type.reminder_ids.ids)] or []
        partner_ids = list(set([employee.user_id.partner_id.id] + [partner.id]))
        return {
            'name': _('%s with %s', appointment_type.name, name),
            'start': date_start.strftime(dtf),
            # FIXME master
            # we override here start_date(time) value because they are not properly
            # recomputed due to ugly overrides in event.calendar (reccurrencies suck!)
            #     (fixing them in stable is a pita as it requires a good rewrite of the
            #      calendar engine)
            'start_date': date_start.strftime(dtf),
            'stop': date_end.strftime(dtf),
            'allday': False,
            'duration': duration,
            'description': description,
            'alarm_ids': alarm_ids,
            'location': appointment_type.location,
            'partner_ids': [(4, pid, False) for pid in partner_ids],
            'categ_ids': [(4, categ_id.id, False)],
            'appointment_type_id': appointment_type.id,
            'user_id': employee.user_id.id,
        }

    # @http.route('/shop/payment/validate', type='http', auth="public", website=True, sitemap=False)
    # def shop_payment_validate(self, transaction_id=None, sale_order_id=None, **post):
    #     print("\n\n --- in --shop_payment_validate:", transaction_id, sale_order_id, post)
    #     """ Method that should be called by the server when receiving an update
    #     for a transaction. State at this point :
    #
    #      - UDPATE ME
    #     """
    #     # if sale_order_id is None:
    #     #     order = request.website.sale_get_order()
    #     # else:
    #     #     order = request.env['sale.order'].sudo().browse(sale_order_id)
    #     #     assert order.id == request.session.get('sale_last_order_id')
    #     #
    #     # if transaction_id:
    #     #     tx = request.env['payment.transaction'].sudo().browse(transaction_id)
    #     #     assert tx in order.transaction_ids()
    #     # elif order:
    #     #     tx = order.get_portal_last_transaction()
    #     # else:
    #     #     tx = None
    #     #
    #     # if not order or (order.amount_total and not tx):
    #     #     return request.redirect('/shop')
    #     #
    #     # if order and not order.amount_total and not tx:
    #     #     order.with_context(send_email=True).action_confirm()
    #     #     return request.redirect(order.get_portal_url())
    #     #
    #     # # clean context and session, then redirect to the confirmation page
    #     # request.website.sale_reset()
    #     # if tx and tx.state == 'draft':
    #     #     return request.redirect('/shop')
    #
    #
    #     return request.redirect('/shop/confirmation')



    @http.route(['/shop/confirmation'], type='http', auth="public", website=True, sitemap=False)
    def shop_payment_confirmation(self, **post):
        """ End of checkout process controller. Confirmation is basically seing
        the status of a sale.order. State at this point :

         - should not have any context / session info: clean them
         - take a sale.order id, because we request a sale.order and are not
           session dependant anymore
        """
        sale_order_id = request.session.get('sale_last_order_id')
        send_again = request.session.get('send_again')
        event_id = request.session.get('event')
        if sale_order_id:
            employee = request.env['hr.employee'].sudo().search([('id', '=', send_again['employee'])])
            appointment_type = request.env['calendar.appointment.type'].sudo().search([('id', '=', send_again['appointment_type'])])
            date_start=send_again['date_start']
            date_end=send_again['date_end']
            Partner = request.env['res.partner'].sudo().search([('id', '=', send_again['Partner'])])
            duration=send_again['duration']
            description=send_again['description']
            name=send_again['name']

            order = request.env['sale.order'].sudo().browse(sale_order_id)
            event = request.env['calendar.event'].with_context(
                mail_notify_author=True,
                allowed_company_ids=employee.user_id.company_ids.ids,
            ).sudo().create(
                self._prepare_calendar_values(appointment_type, date_start, date_end, duration, description, name,
                                              employee, Partner)
            )
            event.attendee_ids.write({'state': 'accepted'})
            return request.redirect('/calendar/view/%s?partner_id=%s&%s' % (event.access_token, Partner.id, keep_query('*', state='new')))

        else:
            if (sale_order_id and not event_id):
                order = request.env['sale.order'].sudo().browse(sale_order_id)
                return request.render("website_sale.confirmation", {'order': order})
            else:
                return request.redirect('/appointment/confirmation')


