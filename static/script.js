async function reviewCode(){

    const code=document.getElementById("code").value;

    if(code.trim()==""){
        alert("Please paste some code.");
        return;
    }

    document.getElementById("result").innerHTML="Reviewing... Please wait.";

    const response=await fetch("/review",{

        method:"POST",

        headers:{
            "Content-Type":"application/json"
        },

        body:JSON.stringify({
            code:code
        })

    });

    const data=await response.json();

    document.getElementById("result").innerHTML=data.result;

}