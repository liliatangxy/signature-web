var express = require('express');
var app = require('express')();
var server = require('http').Server(app);

server.listen(8000);

app.get('/', function (req, res) {
  res.sendfile(__dirname + '/index.html');
});

app.use(express.static(__dirname + "")); //use static files in ROOT/public folder
app.use(express.static('public'));



