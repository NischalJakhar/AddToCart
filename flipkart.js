//var counter;
counter = JSON.parse(localStorage.getItem('counterofcart'));
tobuylist  = JSON.parse(localStorage.getItem('tobuy'));


if(!counter){
    counter=0;
    localStorage.setItem('counterofcart',JSON.stringify(counter))
}



if(!tobuylist){
    tobuylist=[];
    localStorage.setItem('tobuy',JSON.stringify(tobuylist))
}


window.onload = function() {


    var count = document.getElementById('count');
    var libutton = document.getElementById('libutton');
    oc = document.getElementById('overlay-content');
    refreshCart();




    libutton.onclick = function(){
        addToCart(this.previousSibling.previousSibling.currentSrc);
        refreshCart();
    }
}



addToCart = function(value){

    var object1 = {item:value};
    tobuylist.push(object1);
    counter = Number(count.innerText) + 1;
    console.log(counter);

    localStorage.setItem('counterofcart',JSON.stringify(counter));
    localStorage.setItem('tobuy',JSON.stringify(tobuylist))



}


var refreshCart = function(a) {

    tobuylist=JSON.parse(localStorage.getItem('tobuy'))
    var string = ""
    for(var i=0;i<tobuylist.length;i++ ){
        var obj = tobuylist[i]

        string+='<img src=' + obj.item + '>';
    }
    oc.innerHTML=string;
    counter = JSON.parse(localStorage.getItem('counterofcart'))

    count.innerHTML = counter;

}





openNav = function(){
    document.getElementById("myNav").style.height = "100%";
}
function closeNav() {
    document.getElementById("myNav").style.height = "0%";
}


