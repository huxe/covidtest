$(document).ready(function(){
    $(document).on('change','#manager_add_yn',function(){
    var text = document.getElementById("myDIV");
        if (this.checked){

            text.style.display = "block";
            $('#manager_name').prop('required',true);
            $('#manager_email').prop('required',true);
            $('#manager_phone').prop('required',true);

        }
        else {
            text.style.display = "none";
            $('#manager_name').removeAttr('required');
            $('#manager_email').removeAttr('required');
            $('#manager_phone').removeAttr('required');
        }
    });

    $(document).on('change','#account_add_yn',function(){
        var text_acc = document.getElementById("AccountentDiv");
        if (this.checked){

            text_acc.style.display = "block";
            $('#accountent_name').prop('required',true);
            $('#accountent_email').prop('required',true);
            $('#accountent_phone').prop('required',true);

        }
        else {
            text_acc.style.display = "none";
            $('#accountent_name').removeAttr('required');
            $('#accountent_email').removeAttr('required');
            $('#accountent_phone').removeAttr('required');
        }
    });

    $(document).on('change','#shipping_add_yn',function(){
        var text_ship = document.getElementById("ShippingDiv");
        if (this.checked){

            text_ship.style.display = "none";
            $('#shipping_name').removeAttr('required');
            $('#shipping_email').removeAttr('required');
            $('#shipping_phone').removeAttr('required');
            $('#shipping_address').removeAttr('required');
        }
        else {
            text_ship.style.display = "block";
            $('#shipping_name').prop('required',true);
            $('#shipping_email').prop('required',true);
            $('#shipping_phone').prop('required',true);
            $('#shipping_address').prop('required',true);
        }
    });
})