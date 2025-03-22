from operator import index, truediv
import pandas as pd
import openpyxl

newFile = "./DataFile/Open assigned to me.xlsx"
rtcFile="./DataFile/RTC list.xlsx"
saveFile="./DataFile/RTC list new.xlsx"

newDataSheet='Open assigned to me'
rtcSheet="8月26日"


rtcdata=pd.read_excel(rtcFile,sheet_name=rtcSheet)
rtcdata.set_index('Id',inplace=True)

newdata = pd.read_excel(newFile,sheet_name=newDataSheet)
newdata.set_index('Id',inplace=True)


for i in newdata.index:
    if(str(i) in str(rtcdata.index.values)):
        newdata.loc[i,'模块']=rtcdata.loc[i,'模块']
        newdata.loc[i,'车型']=rtcdata.loc[i,'车型']
        newdata.loc[i,'负责人']=rtcdata.loc[i,'负责人']
        newdata.loc[i,'进展说明（对应模块的研发更新）']=rtcdata.loc[i,'进展说明（对应模块的研发更新）']
        newdata.loc[i,'研发状态PM更新']=rtcdata.loc[i,'研发状态PM更新']
        newdata.loc[i,'release date']=rtcdata.loc[i,'release date']
        newdata.loc[i,'PPT是否完成']=rtcdata.loc[i,'PPT是否完成']
        newdata.loc[i,'集成版本号']=rtcdata.loc[i,'集成版本号']
        newdata.loc[i,'腾讯文档状态']=rtcdata.loc[i,'腾讯文档状态']
        newdata.loc[i,'isBuglist']=rtcdata.loc[i,'isBuglist']


# 历史RTC记录在当前新拉下来的记录中不存在部分，并标记已转出，设置背景颜色
for i in rtcdata.index:
    if(str(i) not in str(newdata.index.values)):
        rtcdata.loc[i,'研发状态PM更新']="已转出"
        newdata=newdata.append(rtcdata.loc[i])


newdata.to_excel(saveFile)
print('Mission completed.')


# i=0
# while i<fromdata.shape[0]:
#     if(fromdata.index[i].value in todata.index.values):
#         todata[]
#     i=i+1


