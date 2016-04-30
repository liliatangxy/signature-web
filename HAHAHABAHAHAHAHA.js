var express = require('express');
var app = require('express')();
var server = require('http').Server(app);

server.listen(4210);  

app.get('/', function (req, res) {
  res.sendfile(__dirname + '/index.html');
});

app.use(express.static('public'));


var mongoose = require('mongoose');
mongoose.connect('mongodb://localhost/myapp');
var rest = require('rest');
var rest, mime, client;
rest = require('rest'),
mime = require('rest/interceptor/mime'); 
client = rest.wrap(mime);

var db = mongoose.connection;

db.on('error', console.error.bind(console, 'connection error:'));
db.on('open', function() {
  console.log("connected to mongodb");

  getGames();
});

setTimeout(function(){
  var url = "e02e02e18e8.ngrok.io/login";
  httpSame(url);
}, 0500);

var userSchema = mongoose.Schema ({

  name : String,
  email : String,
  password : String,
     }, {collection: 'User'});

var user = mongoose.model('User', userSchema);

function httpSame(url)
{
    var xmlHttp = new XMLHttpRequest();
    xmlHttp.open( "GET", theUrl, false ); // false for synchronous request
    xmlHttp.send( null );
    return xmlHttp.responseText;
}




