import pandas as pd, numpy as np, json
np.random.seed(42)
R='data/reports_csi_strengthening/'
f=pd.read_csv(R+'csi_predictions_full_stratified.csv',usecols=['row_index','y_true','y_score','y_pred'])
n=pd.read_csv(R+'csi_predictions_no_outcome_stratified.csv',usecols=['row_index','y_score','y_pred'])
m=f.merge(n,on='row_index',suffixes=('_f','_n'))
y=m['y_true'].to_numpy(); sf=m['y_score_f'].to_numpy(); sn=m['y_score_n'].to_numpy()
pf=m['y_pred_f'].to_numpy(); pn=m['y_pred_n'].to_numpy()
def ap(y,s):
    o=np.argsort(-s,kind='mergesort'); yy=y[o]; tp=np.cumsum(yy); fp=np.cumsum(1-yy)
    P=tp/(tp+fp); Rr=tp/tp[-1]; Rp=np.concatenate([[0],Rr[:-1]]); return float(np.sum((Rr-Rp)*P))
def mf1(y,yp):
    def f1(t):
        TP=np.sum((yp==t)&(y==t));FP=np.sum((yp==t)&(y!=t));FN=np.sum((yp!=t)&(y==t))
        P=TP/(TP+FP) if TP+FP else 0;Rr=TP/(TP+FN) if TP+FN else 0
        return 2*P*Rr/(P+Rr) if P+Rr else 0
    return (f1(0)+f1(1))/2
import sys
dAP=ap(y,sf)-ap(y,sn); dF1=mf1(y,pf)-mf1(y,pn)
print("dAP_point",round(dAP,4),"dF1_point",round(dF1,4));sys.stdout.flush()
N=len(y); B=120; da=np.empty(B); dd=np.empty(B)
for i in range(B):
    s=np.random.randint(0,N,N)
    da[i]=ap(y[s],sf[s])-ap(y[s],sn[s]); dd[i]=mf1(y[s],pf[s])-mf1(y[s],pn[s])
res={'dAP_point':round(dAP,4),'dAP_ci95':[round(float(np.percentile(da,2.5)),4),round(float(np.percentile(da,97.5)),4)],
     'dMacroF1_point':round(dF1,4),'dMacroF1_ci95':[round(float(np.percentile(dd,2.5)),4),round(float(np.percentile(dd,97.5)),4)],
     'B':B}
import json
d=json.load(open('data/reports_q1audit/q1audit_addons.json')); d['paired_diff_full_minus_nooutcome']=res
json.dump(d,open('data/reports_q1audit/q1audit_addons.json','w'),indent=2)
print(json.dumps(res,indent=2))
