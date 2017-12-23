from opencc import OpenCC
from urllib.parse import unquote
from optparse import OptionParser
import re
import json
import msgpack
import sys

# 一些初始化
openCC = OpenCC('t2s')

# 读取文件的函数
# 参数为文件名。输出为(处理的文章数, 以文章为单位的无链接文本，链接信息列表)
def read_file(filename) :
	
	# 打开文件
	myfile = open(filename, 'r', encoding = 'utf-8')
	
	# 文章ID，文章的URL，文章标题
	id, URL, Title = 0, '', ''
		
	# 所有文章的信息
	Articles = []
	
	# 不含链接的文本（临时变量）
	noLinkString = ''
	# 当前文章的信息（临时变量）
	nowArticle = {}
	
	lineN = 0
	t1 = myfile.readline()
	t2 = ''
	while len(t1) :
		lineN += 1
			
		# 提取文章信息
		nPos = t1.find('<doc id="')
		if nPos != -1 :	
			pEnd_Of_ID = t1.find('" url="', nPos)
			pEnd_Of_URL = t1.find('" title="', pEnd_Of_ID)
			pEnd_Of_Title = t1.find('">', pEnd_Of_URL)
			
			id = t1[nPos + 9 : pEnd_Of_ID]
			URL = t1[pEnd_Of_ID + 7 : pEnd_Of_URL]
			Title = t1[pEnd_Of_URL + 9 : pEnd_Of_Title]
			
			# 清零临时变量
			noLinkString = ''
			nowArticle = {'title' : Title, 'id' : id, 'text' : '', 'links' : []}
		
		elif t1.find('</doc>') != -1 :
			# 文档结束
			nowArticle['text'] = noLinkString
			Articles.append(nowArticle)
		else :
			# 当一行太短时（可能为空行），跳过
			if (len(t1) < 3) :
				t1 = myfile.readline()
				continue
			
			# 有些段落是多行的，跨过它
			t2 = myfile.readline()
			lineN += 1
			while (len(t2) > 3 and t2.find('</doc>') == -1) :
				t1 = t1.strip('\r\n ') + t2
				t2 = myfile.readline()
				lineN += 1
			
			# 换成简体中文的表达
			p = re.compile('\\-{([^{}]*?)zh-hans:([^{}]*?);([^{}]*?)}\\-')
			t1 = p.sub(r'\2', t1)
			p = re.compile('\\-{([^{}]*?)zh-cn:([^{}]*?);([^{}]*?)}\\-')
			t1 = p.sub(r'\2', t1)
			p = re.compile('\\-{([^{}]*?)zh-hant:([^{}]*?);([^{}]*?)}\\-')
			t1 = p.sub(r'\2', t1)
			p = re.compile('\\-{([^{}]*?)zh-tw:([^{}]*?);([^{}]*?)}\\-')
			t1 = p.sub(r'\2', t1)
			p = re.compile('\\-{([^{}]*?)zh-hk:([^{}]*?);([^{}]*?)}\\-')
			t1 = p.sub(r'\2', t1)
			
			# 统计该段落里的链接
			nPos = 0
			while nPos != -1 :
				New_nPos = t1.find('<a href="', nPos)
				
				# 将链接前的部分加入无链接文本，并更新划分信息
				if New_nPos != -1 :
					noLinkString += t1[nPos : New_nPos]
				else :
					noLinkString += t1[nPos : ]
					break
				
				nPos = New_nPos
					
				pEnd_Of_Href = t1.find('">', nPos)
				pEnd_Of_Link = t1.find("</a>", pEnd_Of_Href)
				
				if pEnd_Of_Href == -1 or pEnd_Of_Link == -1 :
					if t2.find('</doc>') == -1 :
						t1 = myfile.readline()
					else :
						t1 = t2
					continue
				
				# 获取到链接的内容和链接目标地址（暂时不使用）
				Anchor = openCC.convert(t1[pEnd_Of_Href + 2 : pEnd_Of_Link])
				Target = openCC.convert(unquote(t1[nPos + 9 : pEnd_Of_Href]))
				
				if len(Anchor) > 0 :
					# 添加链接内容到链接列表
					nowArticle['links'].append({'start' : len(noLinkString), 'len' : len(Anchor), 'target' : Target})
					# 添加链接内容到无链接标记的文本
					noLinkString += Anchor

				nPos = pEnd_Of_Link + 4
			
			# 把无链接的平文本转换成简体
			noLinkString = openCC.convert(noLinkString)
		
		# 判断是否是文档的结尾
		if t2.find('</doc>') == -1 : 
			t1 = myfile.readline()
		else :
			t1 = t2
		
	myfile.close()
	
	return Articles

if __name__ == '__main__' :

	usage = '%prog [options] arg'
	parser = OptionParser(usage)
	parser.add_option('-i', '--infile', dest = 'infilename', help = 'input file name')
	parser.add_option('-o', '--outfile', dest = 'outfilename', help = 'output file name')
	parser.add_option('-m', '--msgpack', action = 'store_true', dest = 'useMsgPack', help = 'use python-msgpack as output format. JSON will be used instead if this option is not set.')
	
	(options, args) = parser.parse_args()
	
	if options.infilename == None :
		print('Error: No input file. Run "python %s -h" for help.' % sys.argv[0])
		sys.exit(2)
	elif options.outfilename == None :
		print('Error: No output file. Run "python %s -h" for help.' % sys.argv[0])
		sys.exit(2)
		
	process_result = read_file(options.infilename)
	
	if not options.useMsgPack :
		with open(options.outfilename, 'w', encoding = 'utf-8') as file :
			file.write(json.dumps(process_result))
	else :
		with open(options.outfilename, 'wb') as file :
			file.write(msgpack.packb(process_result))