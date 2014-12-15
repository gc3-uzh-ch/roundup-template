
function retire(qid){
    var form = $("form");
    // form.append("<input type='hidden' name='@action' value='retire' />");
    form.append("<input type='hidden' name='qid' value='" + qid + "' />");
    // form.append("<inpyt type='submit' value='submit' />");
    form.submit();
}
