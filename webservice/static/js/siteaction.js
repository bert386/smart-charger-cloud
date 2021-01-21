var socket;

function sendEvent(obj) {
	socket.emit('my_event', {data: obj.getAttribute('id')});
	console.log ({data: obj.getAttribute('id')});
}
$(document).ready(function() {
	// Use a "/test" namespace.
	// An application can open a connection on multiple namespaces, and
	// Socket.IO will multiplex all those connections on a single
	// physical channel. If you don't care about multiple channels, you
	// can set the namespace to an empty string.
	namespace = '/evsecontoller';
	// Connect to the Socket.IO server.
	// The connection URL has the following format:
	//     http[s]://<domain>:<port>[/<namespace>]
	socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port + namespace);
	// Event handler for new connections.
	// The callback function is invoked when a connection with the
	// server is established.
	//socket.on('connect', function() {
	//	socket.emit('my_event', {data: 'I\'m connected!'});
	//});
	// Event handler for server sent data.
	// The callback function is invoked whenever the server emits data
	// to the client. The data is then displayed in the "Received"
	// section of the page.
	
	socket.on('loadstatus', function(msg) {
		console.log ("connected");
		console.log (msg.data);
		//var html_text = '';
		var site_array = JSON.parse(msg.data);
		if (!Array.isArray(site_array))
			return ;
		SiteLoadData(msg.data);
		
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

    var html='<h2>Add Site</h2><form class="form add" id="form_company" data-id="" novalidate><div class="input_container">';
        html +='<label for="company_name">Site Name: <span class="required">*</span></label><div class="field_container">';
        html +='<input type="text" class="text" name="sitename" id="sitename" value="" required></div></div>';
        html +='<div class="input_container"><label for="industries">longitude: <span class="required">*</span></label>';
        html +='<div class="field_container"><input type="number" class="text" name="longitude" id="longitude" value="" required>';
        html +='</div></div><div class="input_container"><label for="revenue">latitude: <span class="required">*</span></label>';
        html +='<div class="field_container"><input type="number" class="text" name="latitude" id="latitude" value="" required></div>';
        html +='</div><div class="button_container"><button type="submit" class="btn btn-primary">Add Site</button></div></form>';
    $('.lightbox_content').html(html);    
    $('#form_company').attr('class', 'form add');
    $('#form_company').attr('data-id', '');
    $('#form_company .field_container label.error').hide();
    $('#form_company .field_container').removeClass('valid').removeClass('error');
    $('#form_company #sitename').val('');
    $('#form_company #longitude').val('');
    $('#form_company #latitude').val('');

    show_lightbox();
  });


  $(document).on('click', '#function_add', function(e)
  {
    e.preventDefault();
    var sitename = $(this).data('name');
    var html='<h2>Add Station</h2><form class="form add" id="form_company" data-id="" novalidate><div class="input_container">';
        html +='<label for="company_name">Station Name: <span class="required">*</span></label><div class="field_container">';
        html +='<input type="text" class="text" name="shadowName" id="shadowName" value="" required></div></div>';
        html +='<div class="input_container"><label for="industries">Station Serial: <span class="required">*</span></label>';
        html +='<div class="field_container"><input type="text" class="text" name="stationSerial" id="stationSerial" value="" required>';
        html +='</div></div><div class="button_container"><button type="submit" class="btn btn-primary">Add Station</button></div></form>';
    $('.lightbox_content').html(html);    
    $('#form_company').attr('class', 'form station');
    $('#form_company').attr('data-name', sitename);
    $('#form_company .field_container label.error').hide();
    $('#form_company .field_container').removeClass('valid').removeClass('error');
   
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
      var request   = $.ajax
      ({
        url:          '/addsite',
        data:         form_data,
        type:         'POST',
        success: function(response)
        {
            hide_loading_message();
            window.location.href='/sitemanger';
        },
        error: function(error) 
        {
            console.log(error);
        }
      });

    }
  });

  $(document).on('submit', '#form_company.station', function(e)
  {
  	e.preventDefault();
    var sitename        = $('#form_company').attr('data-name');
    // Validate form
    if (form_company.valid() == true)
    {

      // Send company information to database
      hide_lightbox();
      show_loading_message();
      var form_data = $('#form_company').serialize();
      	  form_data +='&sitename='+sitename;	
      var request   = $.ajax
      ({
        url:          '/addstation',
        data:         form_data,
        type:         'POST',
        success: function(response)
        {
            hide_loading_message();
            window.location.href='/sitemanger';
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
    var sitename = $(this).data('name');
    if (confirm("Are you sure you want to delete '" + sitename + "'?")){
      show_loading_message();
      var request = $.ajax
      ({
        url:          '/delsite',
        data:         'sitename='+sitename,
        type:         'POST',
        success: function(response)
        {
            hide_loading_message();
            window.location.href='/sitemanger';
        },
        error: function(error) 
        {
            console.log(error);
        }
      });
      
    }
  });
  $(document).on('click', '#function_delete_station', function(e)
  {
    e.preventDefault();
    var shadowName = $(this).data('name');
    var sitename = $(this).data('id');
    if (confirm("Are you sure you want to delete '" + shadowName + "'?")){
      show_loading_message();
      var request = $.ajax
      ({
        url:          '/delstation',
        data:         'shadowName='+shadowName+'&sitename='+sitename,
        type:         'POST',
        success: function(response)
        {
            hide_loading_message();
            window.location.href='/sitemanger';
        },
        error: function(error) 
        {
            console.log(error);
        }
      });
      
    }
  });


  $(document).on('click', '.status', function(e)
   {
        e.preventDefault();
        if($(this).children().first().val() =='false')
        	var status ='true';
        else
            var status ='false';
        
        var shadowName = $(this).data('name');
        var sitename = $(this).data('id');
        var request   = $.ajax
        ({
            url:          '/updatestation',
            data:         'shadowName='+shadowName+'&sitename='+sitename+'&activate='+status,
            type:         'POST',
            context: this,
            success: function(response)
            {
            	if(status =='true')
                {
                   $(this).css('color','#1BB015');
                   $(this).children().first().val('true');
                }
                else
                {
                	$(this).children().first().val('false');
                	$(this).css('color','');
                }       
            },
            error: function(error) 
            {
                //console.log(error);
            }
        });
       
    });

   $(document).on('click', '.function_supply', function(e)
   {
        e.preventDefault();
               
        var sitename = $(this).data('name');
        var OriginalContent = $(this).text();

	    //$(this).addClass("cellEditing");
	    $(this).html("<input type='number' style='width:50px;line-height:15px;' class='spinner' name='value' value='"+OriginalContent+"'>");

	    //var spinner = $( ".spinner" ).spinner();
	    //spinner.spinner( "value", OriginalContent );

	    $(this).children().first().focus();

	    $(this).children().first().keypress(function (e)
	    {
	        if (e.which == 13) 
	        {
	        	var newContent = $(this).val();
	        	$(this).parent().text(newContent);
	        	var request   = $.ajax
		        ({
		            url:          '/updatesite',
		            data:         'sitename='+sitename+'&supply='+newContent,
		            type:         'POST',
		            success: function(response)
		            {
		            	
	            		
		            },
		            error: function(error) 
		            {
		                //console.log(error);
		            }
		        });
	            
	            
	        }
	    });

		 $(this).children().first().blur(function(){
		    $(this).parent().text(OriginalContent);
		    
		 });
	 });

   $(document).on('click', '.footable-row-detail-value', function(e)
   {
        e.preventDefault();
        
        var shadowName = $(this).parent().parent().data('name');
    	var sitename = $(this).parent().parent().data('id');

        var id = $(this).attr('id');
        if(id =="charge_max" || id =="present_power")
        {

        	var OriginalContent = $(this).text();
    
		    $(this).find('span').html("<input type='number' style='width:50px;line-height:15px;' value='"+ OriginalContent +"''>");
		    $(this).find('span').children().first().focus();

		    $(this).find('span').children().first().keypress(function (e)
		    {
		        if (e.which == 13) 
		        {
		        	var newContent = $(this).val();
		        	$(this).parent().text(newContent);
		        	var request   = $.ajax
			        ({
			            url:          '/updatestation',
			            data:         'shadowName='+shadowName+'&sitename='+sitename+'&'+id+'='+newContent,
			            type:         'POST',
			            success: function(response)
			            {
			            	
		            		
			            },
			            error: function(error) 
			            {
			                //console.log(error);
			            }
			        });
		            
		            
		        }
		    });

			 $(this).children().first().blur(function(){
			    $(this).parent().text(OriginalContent);
			    
			 });
			}
	 });
  
});
