import glob,os,json

sorted_tx=[]
for each in  glob.glob('./tx/*.json'):
	data=json.loads(open(each).readline())[0]
	if data['invalid'] != False or data['index'][:8]=='(mailbox':
		sorted_tx.append((each, data['invalid'],data['block']))
		

for each in sorted_tx:
	print each
sorted_tx=sorted(sorted_tx, key=lambda x: x[2])
print len(sorted_tx)
for each in sorted_tx:
	print each
	redo=False
	if each[1][:3]=='non':
		redo=True 
	each=each[0][5:-5]
	os.popen('python $TOOLSDIR/msc_parse.py -s 0 -d -t '+each+' -r $TOOLSDIR 2>&1 > parsed2.log')
	if redo:
		os.popen('python $TOOLSDIR/msc_parse.py -s 0 -d -t '+each+' -r $TOOLSDIR 2>&1 > parsed2.log')
