const app =require('express')();
const PORT = 8080

app.get('/data',(req,res)=>{
	res.status(200).send({data:"works"})
})

app.listen(PORT,() => {})

