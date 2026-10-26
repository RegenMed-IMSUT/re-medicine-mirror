
$(document).ready(function(){


	$('.seren-img-hover').hover(
		function(){
			$(this).find('.caption').slideDown(500);
		},
		function(){
			$(this).find('.caption').slideUp(500);
		}
	);
		

});		


