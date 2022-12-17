::echo param0=%0

set my_param=%1
::echo %my_param%

set my_param_1=%my_param:~9%
::echo %my_param_1%

set my_param_2=%my_param_1:~0,-2%
echo %my_param_2%

pause
python C:/cc/python/epwork/dms_vs_2/dms_vs_3.py  --int_job_id=%my_param_2%




pause

