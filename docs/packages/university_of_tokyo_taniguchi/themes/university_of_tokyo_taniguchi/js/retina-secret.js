/*
 * https://on-ze.com/archives/3131
 */
$(function(){
	var retinaCheck = window.devicePixelRatio;
	if(retinaCheck >= 2) { // Retinaディスプレイのときを分岐させている
		$('img.retina').each( function() {
			var retinaimg = $(this).attr('src').replace(/\.(?=(?:png|jpg|jpeg)$)/i, '@2x.');
			$(this).attr('srcset', retinaimg + " 2x");
		});
	}
});
