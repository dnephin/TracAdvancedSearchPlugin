

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
