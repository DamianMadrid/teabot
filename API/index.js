const { response } = require('express');
const express = require('express');
const cors = require('cors');
const app = express();
var sqlite3 = require('sqlite3').verbose();
var db = new sqlite3.Database('C:/Users/asdf1/Documents/Personal_projects/YARAPT/data/prices.db');
const PORT = 8000
app.use(cors());
app.get("/prices", (req, res) => {

    id = req.query["id"]
    if (id) {
        db.get("select * from prices where prod_id = ?", [id], (err, row) => {
            if (err) {
                res.status(400)
                res.send({ "err": err.name })
                return;
            }
            if (row) {
                res.status(200)
                res.send({"data":row})
                return;
            } else {
                res.status(404)
                res.send({ "err": "no such id" })
                return;
            }
        })
        return;
    }

    db.all("select * from prices", (err, row) => {
        if (err) {
            res.status(400)
            res.send({ "err": err.name })
        }
        if (row) {
            res.status(200)
            res.send({"data":row})
        }
    })
    return;


})

app.listen(PORT)
