

function next_page(start_point_list) {
	var form = $('#fullsearch');

	query_string = form.serialize();
	// Increase page count
	var page = parseInt(form.find('input[name=page]').val()) + 1;
	query_string = query_string.replace(new RegExp("page=\\d+"), 'page='+page);

	// Set start points
	query_string += '&' + $.param(start_point_list)

	document.location.search = '?' + query_string;
	return false;
}

function add_author_input(elem) {
	$(elem).parent('div').before(
		'<div><input type="text" name="author"/> ' +
		'<a href="#" onclick="return remove_author_input(this)">remove</a></div>'
	);
	return false;
}

function remove_author_input(elem) {
	$(elem).parent('div').remove();
	return false;
}

$(document).ready(function() {
	$('#fullsearch input').change(function() {
		$('#fullsearch input[name="page"]').val(1);
	})
})
