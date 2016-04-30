var myvar;

function myFunction()
{
	var name = $('#input-name').val();
	myvar = window.setInterval(login, 500);
	
}

function login()
{
	var name = document.getElementById('input-name').value;
	$.post("http://7ac770f8.ngrok.io/loggedin", {username: "Kevin_Frans"}, function(result){
        console.log("im back bby" + result);
        if(result == "false")
        {

        }
        else
        {
        	window.location.href = "http://troll.com"
        	console.log("i am now logged in ");
        	clearInterval(myvar);
        }
    });

}

