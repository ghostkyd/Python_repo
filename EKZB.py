import sys
import os
import shutil
import subprocess
import time
import configparser
#导出kzb
def Export_KZB_Script_PC(KZ_KZB_Path,KZ_MAIN_Path):
    with open("ExportKZB.txt","w") as f:
        f.write("LoadProject " +KZ_MAIN_Path+ " \n")
        f.write("ExportAllProjectBinaries "+KZ_KZB_Path+" true true \n")
        f.write("ExportBakedThemeBinaries \n")
        f.write("ExitApplication \n")
    f.close()
KZ_MAIN_Path = "D:/KanziWorkspace_3_6_13_57/Projects/test/Tool_project/test.kzproj"
KZ_KZB_Path = "D:/KanziWorkspace_3_6_13_57/Projects/test/Application/bin"
Export_KZB_Script_PC(KZ_KZB_Path,KZ_MAIN_Path)
KZ_EXE_Path = "D:/Program Files/Rightware/Kanzi 3_6_13_57/Studio/Bin/KanziStudio.exe"
path = "D:/工具"
KZBResult = subprocess.getoutput('"'+KZ_EXE_Path + '"' + ' /Script='+path+'\ExportKZB.txt')
print(KZBResult)


def CPKZB(source_path,target_path):
    CFG_Name_Len = KZ_MAIN_Path.split("/")
    CFG_Name = CFG_Name_Len[len(CFG_Name_Len)-1].split(".kzproj")[0]
    if not os.path.exists(target_path):
        os.makedirs(target_path)
    if os.path.exists(source_path):
        for root, dirs, files in os.walk(source_path):
            for file in files:
                if file.endswith(".kzb"):
                    src_file = os.path.join(root, file)
                    shutil.copy(src_file, target_path)
                    print(src_file)
                elif(file == CFG_Name+".kzb.cfg"):
                    src_file = os.path.join(root, file)
                    shutil.copy(src_file, target_path)
                    print(src_file)
            for dir in dirs:
                if "Vehicle=" in str(dir):
                    src_file = os.path.join(root, dir)
                    shutil.copy(src_file, target_path)
                    print(src_file)
source_path = "D:/KanziWorkspace_3_6_13_57/Projects/test/Application/bin"
target_path = "D:/工具/kzb"
CPKZB(source_path,target_path)
