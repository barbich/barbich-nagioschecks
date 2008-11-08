var Infovis = {

	initLayout: function() {
		var size = Window.getSize();
		var header = $('header'), left = $('left'), infovisContainer = $('infovis');
		var headerOffset = header.getSize().y, leftOffset = left.getSize().x;

		var newStyles = {
			'height': Math.floor((size.y - headerOffset) / 1),
			'width' : Math.floor((size.x - leftOffset) / 1)
		};

		infovisContainer.setProperties(newStyles);
		infovisContainer.setStyles(newStyles);
		infovisContainer.setStyles({
			'position':'absolute',
			'top': headerOffset + 'px',
			'left': leftOffset + 'px'
		});
		left.setStyle('height', newStyles.height);
	}
};

function initrunTree() {
    Log.write("Initrun done");
    window.addEvent('domready', function() {
        var rgraph = init();
        new Request.JSON({
                'url':'/dnagmap/stree/',
                onSuccess: function(json) {
                          //load wine dependency tree.
                         rgraph.loadTreeFromJSON(json);
                          //compute positions
                          rgraph.compute();
                          //make first plot
                          rgraph.plot();
                          Log.write("done");
                          rgraph.controller.nodeName = name;
                },
                onFailure: function() {
                        Log.write("failed!");
                }
            }).get();
    });
}

