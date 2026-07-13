(function(){
  const I=window.MatchIQIdentity;
  I.openValidation=id=>I.openDetail(id,true);
  I.saveValidation=async id=>{
    const action=document.getElementById("identityValidationAction")?.value;
    const note=document.getElementById("identityValidationNote")?.value.trim()||"";
    if(action==="update_declared"&&!note){I.notice("Indica la nuova preferenza dichiarata.",true);return}
    try{
      const payload={action,note:action==="update_declared"?null:(note||null),declared_value:action==="update_declared"?note:null};
      await I.api.validate(id,payload); I.closeDetail(); I.notice("Decisione staff salvata. Evidenze e storico sono stati conservati."); await I.load();
    }catch(error){I.notice(error.message,true)}
  };
})();
