@echo on
@set /p CURRENT_DATE=Please input the date: 
python RTCbugsProcessOpenpyxl.py %CURRENT_DATE%
@pause