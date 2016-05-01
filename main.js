var myvar;
var name;

function myFunction()
{
	name = $('#input-name').val();
	myvar = window.setInterval(login, 500);
    $("#login").fadeOut("normal", function() {
        $(this).remove();
    });
    $("#same3").fadeOut("normal", function() {
        $(this).html("<br>"+name+",<br>Please sign using your phone to login");
        $(this).fadeIn("normal");
    });

}

function login()
{
	// var name = document.getElementById('input-name').value;
	$.post("http://7ac770f8.ngrok.io/loggedin", {username: name}, function(result){
        console.log("im back bby" + result);
        if(result == "false")
        {

        }
        else if(result == "true")
        {
        	window.location.href = "secure.html"
        	console.log("i am now logged in ");
        	clearInterval(myvar);
        }
        else
        {
            swal({title: "Error!",   text: "Incorrect signature for " + name + ".",   type: "error",   confirmButtonText: "aw mang" });
        }
    });

}

