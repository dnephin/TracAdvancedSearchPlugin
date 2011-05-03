

function next_page(start_point_list) {
	var form = $('#fullsearch');

	$.each(start_point_list, function(i, start_point) {
		form.append('<input type="hidden" name="' + start_point['name'] +
			'" value="' + start_point['value'] + '" />');
	})

	var page = form.find('input[name=page]');
	page.val(parseInt(page.val()) + 1);
	form.submit();
}

function add_author_input(elem) {
	$(elem).parent('div').before(
		'<div><input type="text" name="author"/> ' +
		'<a href="#" onclick="return remove_author_input(this)">remove</a></div>'
	)
	return false;
}

function remove_author_input(elem) {
	$(elem).parent('div').remove();
	return false;
}
