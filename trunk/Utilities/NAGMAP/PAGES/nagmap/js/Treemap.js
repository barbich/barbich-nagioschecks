var Config={tips:false,titleHeight:13,rootId:"infovis",offset:4,levelsToShow:3,Color:{allow:false,minValue:-100,maxValue:100,minColorValue:[255,0,50],maxColorValue:[0,255,50]}};var TreeUtil={prune:function(B,A){this.each(B,function(D,C){if(C==A&&D.children){delete D.children;D.children=[]}})},getParent:function(A,E){if(A.id==E){return false}var D=A.children;if(D&&D.length>0){for(var C=0;C<D.length;C++){if(D[C].id==E){return A}else{var B=this.getParent(D[C],E);if(B){return B}}}}return false},getSubtree:function(A,D){if(A.id==D){return A}for(var C=0;C<A.children.length;C++){var B=this.getSubtree(A.children[C],D);if(B!=null){return B}}return null},getLeaves:function(B){var C=new Array(),A=Config.levelsToShow;this.each(B,function(E,D){if(D<=A&&(!E.children||E.children.length==0)){C.push({node:E,level:A-D})}});return C},resetPath:function(B){var D=Config.rootId;var A="#"+D+" .in-path";$$(A).each(function(G){G.removeClass("in-path")});var C=$(B.id);var E=function(H){var G=H.getParent();if(G&&G.id!=D){return G}return false};var F=(B)?E(C):false;while(F){F.getFirst().addClass("in-path");F=E(F)}},eachLevel:function(A,F,C,E){if(F<=C){E(A,F);var D=A.children;for(var B=0;B<D.length;B++){this.eachLevel(D[B],F+1,C,E)}}},each:function(A,B){this.eachLevel(A,0,Number.MAX_VALUE,B)}};TreeUtil.Group=new Class({initialize:function(B,A){this.array=B;this.objects=new Array();this.controller=A;this.counter=0},loadNodes:function(F){var D=this,A=this.array.length,B=$merge({onComplete:$lambda()},F);this.counter=0;var E={};if(A>0){for(var C=0;C<A;C++){E[this.array[C].node.id]=this.array[C];this.controller.request(this.array[C].node.id,this.array[C].level,{onComplete:function(I,G){for(var H=0;H<G.children.length;H++){G.children[H]._parent=E[I]}E[I].children=G.children;if(++D.counter==A){B.onComplete()}}})}}else{B.onComplete()}}});var TM={layout:{orientation:"v",vertical:function(){return this.orientation=="v"},horizontal:function(){return this.orientation=="h"},change:function(){this.orientation=this.vertical()?"h":"v"}},innerController:{onBeforeCompute:$lambda(),onAfterCompute:$lambda(),onCreateLabel:$lambda(),onPlaceLabel:$lambda(),onCreateElement:$lambda(),onComplete:$lambda(),onBeforePlotLine:$lambda(),onAfterPlotLine:$lambda(),request:false},config:Config,toStyle:function(B){var C="";for(var A in B){C+=A+":"+B[A]+";"}return C},leaf:function(A){return(A.children==0)},createBox:function(B,D,A){if(!this.leaf(B)){var C=this.newHeadHTML(B,D)+this.newBodyHTML(A,D)}else{var C=this.newLeafHTML(B,D)}return this.newContentHTML(B,D,C)},plot:function(C){var E=(C._coord)?C._coord:C.coord;if(this.leaf(C)){return this.createBox(C,E,null)}for(var B=0,A="",D=C.children;B<D.length;B++){A+=this.plot(D[B])}return this.createBox(C,E,A)},newHeadHTML:function(B,D){var A=this.config;var C={height:A.titleHeight+"px",width:(D.width-A.offset)+"px",left:A.offset/2+"px"};return'<div class="head" style="'+this.toStyle(C)+'">'+B.name+"</div>"},newBodyHTML:function(B,D){var A=this.config;var C={width:(D.width-A.offset)+"px",height:(D.height-A.offset-A.titleHeight)+"px",top:(A.titleHeight+A.offset/2)+"px",left:(A.offset/2)+"px"};return'<div class="body" style="'+this.toStyle(C)+'">'+B+"</div>"},newContentHTML:function(C,E,B){var D={};for(var A in E){D[A]=E[A]+"px"}return'<div class="content" style="'+this.toStyle(D)+'" id="'+C.id+'">'+B+"</div>"},newLeafHTML:function(D,G){var C=this.config;var B=(C.Color.allow)?this.setColor(D):false,E=G.width-C.offset,A=G.height-C.offset;var F={top:(C.offset/2)+"px",height:A+"px",width:E+"px",left:(C.offset/2)+"px"};if(B){F["background-color"]=B}return'<div class="leaf" style="'+this.toStyle(F)+'">'+D.name+"</div>"},setColor:function(D){var E=this.config.Color;var A=D.data[1].value.toFloat();var B=function(G,F){return((E.maxColorValue[G]-E.minColorValue[G])/(E.maxValue-E.minValue))*(F-E.minValue)+E.minColorValue[G]};var C=new Array();C[0]=B(0,A).toInt();C[1]=B(1,A).toInt();C[2]=B(2,A).toInt();return C.rgbToHex()},enter:function(B){var C=B.getParent().id,A=TreeUtil.getSubtree(this.tree,C);this.post(A,C,this.getPostRequestHandler(C))},out:function(){var A=TreeUtil.getParent(this.tree,this.shownTree.id);if(A){if(this.controller.request){TreeUtil.prune(A,this.config.levelsToShow)}this.post(A,A.id,this.getPostRequestHandler(A.id))}},getPostRequestHandler:function(C){var A=this.config,B=this;if(A.tips){this.tips.hide()}return postRequest={onComplete:function(){B.loadTree(C);$(A.rootId).focus()}}},post:function(A,E,B){if(this.controller.request){var D=TreeUtil.getLeaves(TreeUtil.getSubtree(this.tree,E));var C=new TreeUtil.Group(D,this.controller).loadNodes(B)}else{setTimeout(function(){B.onComplete()},1)}},initializeBehavior:function(){var A=$$(".leaf",".head"),B=this;if(this.config.tips){this.tips=new Tips(A,{className:"tool-tip",showDelay:0,hideDelay:0})}A.each(function(C){C.oncontextmenu=$lambda(false);C.addEvents({mouseenter:function(E){var F=false;if(C.hasClass("leaf")){F=C.getParent().id;C.addClass("over-leaf")}else{if(C.hasClass("head")){F=C.getParent().id;C.addClass("over-head");C.getParent().addClass("over-content")}}if(F){var D=TreeUtil.getSubtree(B.tree,F);TreeUtil.resetPath(D)}E.stopPropagation()},mouseleave:function(D){if(C.hasClass("over-leaf")){C.removeClass("over-leaf")}else{if(C.getParent().hasClass("over-content")){C.removeClass("over-head");C.getParent().removeClass("over-content")}}TreeUtil.resetPath(false);D.stopPropagation()},mouseup:function(D){if(D.rightClick){B.out()}else{B.enter(C)}D.preventDefault();return false}})})},loadTree:function(A){$(this.config.rootId).empty();this.loadFromJSON(TreeUtil.getSubtree(this.tree,A))}};TM.SliceAndDice=new Class({Implements:TM,initialize:function(A){this.tree=null;this.shownTree=null;this.tips=null;this.controller=$merge(this.innerController,A);this.rootId=Config.rootId},loadFromJSON:function(C){var A=$(this.rootId),B=this.config;var D={};D.coord={top:0,left:0,width:A.offsetWidth,height:A.offsetHeight+B.titleHeight+B.offset};if(this.tree==null){this.tree=C}this.shownTree=C;this.loadTreeFromJSON(D,C,this.layout.orientation);A.set("html",this.plot(C));this.initializeBehavior(this);this.controller.onAfterCompute(C)},loadTreeFromJSON:function(G,L,D){var E=this.config;var C=G.coord.width-E.offset;var K=G.coord.height-E.offset-E.titleHeight;var O=(G.data&&G.data.length>0)?L.data[0].value/G.data[0].value:1;var A=(D=="h");if(A){var N=(C*O).round();var B=K}else{var B=(K*O).round();var N=C}L.coord={width:N,height:B,top:0,left:0};D=(A)?"v":"h";var F=(!A)?"width":"height";var I=(!A)?"left":"top";var H=(!A)?"top":"left";var M=0;var J=this;L.children.each(function(P){J.loadTreeFromJSON(L,P,D);P.coord[I]=M;P.coord[H]=0;M+=P.coord[F].toInt()})}});TM.Squarified=new Class({Implements:TM,initialize:function(A){this.tree=null;this.shownTree=null;this.tips=null;this.controller=$merge(this.innerController,A);this.rootId=Config.rootId},loadFromJSON:function(B){this.controller.onBeforeCompute(B);var A=$(Config.rootId);B.coord={height:A.offsetHeight-Config.titleHeight,width:A.offsetWidth,top:0,left:0};B._coord={height:A.offsetHeight,width:A.offsetWidth,top:0,left:0};this.loadTreeFromJSON(false,B,B.coord);A.set("html",TM.plot(B));if(this.tree==null){this.tree=B}this.shownTree=B;this.initializeBehavior(this);this.controller.onAfterCompute(B)},worstAspectRatio:function(C,B){if(!C||C.length==0){return Number.MAX_VALUE}var D=0,A=0,E=Number.MAX_VALUE;(function(G){for(var F=0;F<G.length;F++){var H=G[F]._area;D+=H;E=(E<H)?E:H;A=(A>H)?A:H}})(C);return Math.max(B*B*A/(D*D),D*D/(B*B*E))},loadTreeFromJSON:function(G,D,H){if(!(H.width>=H.height&&this.layout.horizontal())){this.layout.change()}var F=D.children,B=this.config;if(F.length>0){this.processChildrenLayout(D,F,H);for(var C=0;C<F.length;C++){var A=F[C].coord.height-(B.titleHeight+B.offset);var E=F[C].coord.width-B.offset;F[C]._coord={width:F[C].coord.width,height:F[C].coord.height,top:F[C].coord.top,left:F[C].coord.left};F[C].coord={width:E,height:A,top:0,left:0};this.loadTreeFromJSON(D,F[C],F[C].coord)}}},processChildrenLayout:function(D,C,F){(function(K,J){var G=K.coord.width*K.coord.height;var I=K.data[0].value.toFloat();for(var H=0;H<J.length;H++){J[H]._area=G*J[H].data[0].value.toFloat()/I}})(D,C);var A=(this.layout.horizontal())?F.height:F.width;C.sort(function(H,G){if(H._area<G._area){return 1}if(H._area==G.area){return 0}return -1});var E=[C[0]];var B=C.slice(1);this.squarify(B,E,A,F)},squarify:function(B,F,A,E){if(B.length+F.length==1){if(B.length==1){this.layoutLast(B,A,E)}else{this.layoutLast(F,A,E)}return}if(B.length>=2&&F.length==0){F=[B[0]];B=B.slice(1)}if(B.length==0){if(F.length>0){this.layoutRow(F,A,E)}return}var D=B[0];if(this.worstAspectRatio(F,A)>=this.worstAspectRatio([D].concat(F),A)){this.squarify(B.slice(1),F.concat([D]),A,E)}else{var C=this.layoutRow(F,A,E);this.squarify(B,[],C.minimumSideValue,C)}},layoutLast:function(B,A,C){B[0].coord=C},layoutRow:function(A,I,F){var K=(function(N){for(var M=0,O=0;M<N.length;M++){O+=N[M]._area}return O})(A);var D=(this.layout.horizontal())?"height":"width";var C=(this.layout.horizontal())?"width":"height";var H=(K/I).round();var G=(this.layout.vertical())?F.height-H:0;var B=0;for(var E=0;E<A.length;E++){var L={};L[D]=(A[E]._area/H).round();L[C]=H;L.top=(this.layout.horizontal())?F.top+(I-L[D]-G):G;L.left=(this.layout.horizontal())?F.left:F.left+B;A[E].coord=L;if(this.layout.horizontal()){G+=L[D]}else{B+=L[D]}}var J={};J[C]=F[C]-H;J[D]=F[D];J.left=(this.layout.horizontal())?F.left+H:F.left;J.top=F.top;J.minimumSideValue=(J[C]>J[D])?J[D]:J[C];if(J.minimumSideValue!=J[D]){this.layout.change()}return J}});