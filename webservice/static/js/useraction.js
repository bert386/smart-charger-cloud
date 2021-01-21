$(document).ready(function() 
{
  $('#dataTables-user').DataTable
  ({
      pageLength: 10,
      responsive: true

  });

   
	jQuery.validator.setDefaults({
    success: 'valid',
    rules: {
      fiscal_year: {
        required: true,
        min:      2000,
        max:      2025
      }
    },
    errorPlacement: function(error, element){
      error.insertBefore(element);
    },
    highlight: function(element){
      $(element).parent('.field_container').removeClass('valid').addClass('error');
    },
    unhighlight: function(element){
      $(element).parent('.field_container').addClass('valid').removeClass('error');
    }
  });
  var form_company = $('#form_company');
  form_company.validate();
  function show_message(message_text, message_type){
    $('#message').html('<p>' + message_text + '</p>').attr('class', message_type);
    $('#message_container').show();
    if (typeof timeout_message !== 'undefined'){
      window.clearTimeout(timeout_message);
    }
    timeout_message = setTimeout(function(){
      hide_message();
    }, 8000);
  }
  // Hide message
  function hide_message(){
    $('#message').html('').attr('class', '');
    $('#message_container').hide();
  }

  // Show loading message
  function show_loading_message(){
    $('#loading_container').show();
  }
  // Hide loading message
  function hide_loading_message(){
    $('#loading_container').hide();
  }

  // Show lightbox
  function show_lightbox(){
    $('.lightbox_bg').show();
    $('.lightbox_container').show();
  }
  // Hide lightbox
  function hide_lightbox(){
    $('.lightbox_bg').hide();
    $('.lightbox_container').hide();
  }
  // Lightbox background
  $(document).on('click', '.lightbox_bg', function(){
    hide_lightbox();
  });
  // Lightbox close button
  $(document).on('click', '.lightbox_close', function(){
    hide_lightbox();
  });

  $(document).on('click', '#add_site', function(e)
  {
    e.preventDefault();

    $('#form_company').attr('class', 'form add');
    $('#form_company').attr('data-id', '');
    $('#form_company .field_container label.error').hide();
    $('#form_company .field_container').removeClass('valid').removeClass('error');
    $('#form_company #userid').val('');
    $('#form_company #email').val('');
    $('#form_company #password').val('');

    show_lightbox();
  });

  $(document).on('submit', '#form_company.add', function(e)
  {
  	e.preventDefault();
    // Validate form
    if (form_company.valid() == true)
    {

      // Send company information to database
      hide_lightbox();
      show_loading_message();
      var form_data = $('#form_company').serialize();
      alert(form_data);
      var request   = $.ajax
      ({
        url:          '/adduser',
        data:         form_data,
        type:         'POST',
        success: function(response)
        {
            hide_loading_message();
            window.location.href='/usermanager';
        },
        error: function(error) 
        {
            console.log(error);
        }
      });

    }
  });

  
  $(document).on('click', '#function_delete', function(e)
  {
    e.preventDefault();
    var userid = $(this).data('id');
    var email = $(this).data('name');

    if (confirm("Are you sure you want to delete '" + userid + "'?")){
      show_loading_message();
      var request = $.ajax
      ({
        url:          '/deluser',
        data:         'userid='+userid+'&email='+email,
        type:         'POST',
        success: function(response)
        {
            hide_loading_message();
            window.location.href='/usermanager';
        },
        error: function(error) 
        {
            console.log(error);
        }
      });
      
    }
  });
  

});
