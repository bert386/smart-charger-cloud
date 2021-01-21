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
	
	socket.on('sitestatus', function(msg) {
		console.log ("connected");
		console.log (msg.data);
		var html_text = '';
		var site_array = JSON.parse(msg.data);
		//var but_text = '';
		if (!Array.isArray(site_array))
			return ;
		initMap(msg.data);
		/*site_array.forEach(function(item, idx)
		{
			item.stations.forEach(function(item1, idx)
			{
				//alert(item1.serialNumber);
			});
			
			if (item.activate)
			{
				but_col = '#78ff3b';
			} else {
				but_col = 'red';
			}
			if (item.connected)
			{
				status = 'connected';
			} else {
				status = 'not connected';
			}
			but_text = '<div id="'+item.shadowName+'" style="font-size: 20px; line-height:30px" onclick="sendEvent(this)"><svg height="25" width="22" style="vertical-align: sub;"> ' +
							'<circle cx="12" cy="15" r="10" stroke="black" stroke-width="1" fill="'+but_col+'" /></svg></div>' ;
			html_text += '<tr><td>'+(idx + 1)+'</td><td>'+item.shadowName+'</td><td>'+but_text+'</td><td>'+status+'</td><td> Temporary Position</td>'+
                        '<td><a href="#"><i class="fa fa-check text-navy"></i></a></td></tr>';
		});*/
		$('#info_list').html(html_text);
	});
});
