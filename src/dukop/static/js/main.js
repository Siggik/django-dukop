$("input.share-text-input").focus(select_all);
$("input.share-text-input").click(select_all);

function select_all() {
   $(this).select();
   $(this).attr("readonly", true);
}

function copy() {
   var copyText = document.querySelector("input.share-text-input");
   copyText.select();
   document.execCommand("copy");
 }

if (document.querySelector(".js-copy")) {
   document.querySelector(".js-copy").addEventListener("click", copy);
}

// Going through timeline events (with a mission to shorten the labels so it won't break the div's)
// ... also, this commit also included a change that would put the data-text as the elements title, so a hover will show the full label
for (var i = document.getElementsByClassName("timeline__event").length - 1; i >= 0; i--) {



   // Calculate the lenght of text and find the width of the surrounding box
   let lengthOfText = measureText(document.getElementsByClassName("timeline__event")[i].getAttribute('data-text'), 16, "italic").width
   let widthOfElement = document.getElementsByClassName("timeline__event")[i].getBoundingClientRect().width

   // If the length seems to be wider than the width
   if (lengthOfText / widthOfElement > .9) {
      let counter = 0; // Counting how much it runs
      
      let allowedNumber = 1 // Starting this check, to see how wide a 1 character label is
      
      // Check, if there's more space (if we shortened it too much with the 1 characters from above)
      let stillMoreSpace = measureText(document.getElementsByClassName("timeline__event")[i].getAttribute('data-text').substring(0, allowedNumber), 16, "italic").width < widthOfElement
      
      while (stillMoreSpace) {

         // Checking again after last run updated the allowedNumber
         stillMoreSpace = measureText(document.getElementsByClassName("timeline__event")[i].getAttribute('data-text').substring(0, allowedNumber), 16, "italic").width + 55 < widthOfElement

         // So if we're out of space, then let's settle on a good 'substring number' to shorten the label by
         if(!stillMoreSpace){
            console.log("Settled on "+allowedNumber+" for now")
            console.log("I ran "+counter+" times")

            // Shortening and inserting the newDataText ...
            let newDataText = document.getElementsByClassName("timeline__event")[i].getAttribute('data-text').substring(0, allowedNumber) + '..'
            document.getElementsByClassName("timeline__event")[i].setAttribute('data-text', newDataText)
         } else {
            ++allowedNumber // Trying with one more character
            ++counter // Just counting, to make sure we're not eternal - see the next if
         }

         // Because this is a hacky solution, I check if it's running amok
         if(counter > 50){
            stillMoreSpace = false;
            console.log("Argh, cancelllll, I ran more than 50 times pr event!")
         }
      }
   }
}


// https://stackoverflow.com/a/4032497/4241528
function measureText(pText, pFontSize, pStyle) {
    var lDiv = document.createElement('div');

    document.body.appendChild(lDiv);

    if (pStyle != null) {
        lDiv.style = pStyle;
    }
    lDiv.style.fontSize = "" + pFontSize + "px";
    lDiv.style.position = "absolute";
    lDiv.style.left = -1000;
    lDiv.style.top = -1000;

    lDiv.textContent = pText;

    var lResult = {
        width: lDiv.clientWidth,
        height: lDiv.clientHeight
    };

    document.body.removeChild(lDiv);
    lDiv = null;

    return lResult;
}




