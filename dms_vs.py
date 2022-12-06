import os, time,json,shutil,sys
from cc import cc_method
from cc.cc_method import GetTestData,DMS,Print,getFlist
from config_ep.epcam import job_operation,epcam_api
from config_ep.epcam_cc_method import EpGerberToODB,Information
from config_g.g_cc_method import Asw
from config import RunConfig
from pathlib import Path
import urllib  # 导入urllib库
import urllib.request
import os,sys,json,shutil
path = os.path.dirname(os.path.realpath(__file__)) + r'/epcam'
sys.path.append(path)
import epcam
import epcam_api
import job_operation
import layer_info
import re
import psycopg2
import requests


def vs_g(job_id):
    epcam.init()
    epcam_api.set_config_path(RunConfig.ep_cam_path)
    Print.print_with_delimiter("G软件VS开始啦！")


    asw = Asw(r'C:\cc\python\epwork\dms_vs\config_g\bin\gateway.exe')  # 拿到G软件
    #清空料号
    asw.clean_g_all_pre_get_job_list(r'//vmware-host/Shared Folders/share/job_list.txt')
    asw.clean_g_all_do_clean(r'C:\cc\share\job_list.txt')



    data = {}  # 存放当前测试料号的每一层的比对结果。
    g_vs_total_result_flag = True  # True表示最新一次G比对通过
    vs_time_g = str(int(time.time()))  # 比对时间
    data["vs_time_g"] = vs_time_g  # 比对时间存入字典
    data["job_id"] = job_id

    # 取到临时目录
    temp_path = r'C:\cc\share\temp' + "_" + str(job_id) + "_" + vs_time_g
    temp_gerber_path = os.path.join(temp_path, 'gerber')
    temp_ep_path = os.path.join(temp_path, 'ep')
    temp_g_path = os.path.join(temp_path, 'g')

    # 下载并解压原始gerber文件
    DMS().get_file_from_dms_db(temp_path, job_id, field='file_compressed', decompress='rar')
    # 悦谱转图
    job_name_ep = os.listdir(temp_gerber_path)[0] + '_ep'
    job_name = os.listdir(temp_gerber_path)[0].lower()
    file_path_gerber = os.path.join(temp_gerber_path, os.listdir(temp_gerber_path)[0])
    out_path = temp_ep_path
    EpGerberToODB().ep_gerber_to_odb_pytest(job_name_ep, 'orig', file_path_gerber, out_path, job_id)

    # 下载G转图tgz，并解压好
    DMS().get_file_from_dms_db(temp_path, job_id, field='file_odb_g', decompress='tgz')

    # 打开job_ep
    job_ep_name = os.listdir(temp_ep_path)[0]
    print("job_name_ep,job_ep_name:", job_name_ep, job_ep_name)
    res = job_operation.open_job(temp_ep_path, job_ep_name)
    print("open ep result:", res)
    all_layer_ep = job_operation.get_all_layers(job_ep_name)
    if len(all_layer_ep) == 0:
        g_vs_total_result_flag = False
        print("最新-EP-ODB++打开失败！！！！！")
    else:
        print('悦谱软件tgz中的层信息：', all_layer_ep)

    # 打开job_g
    job_g_name = os.listdir(temp_g_path)[0]
    job_operation.open_job(temp_g_path, job_g_name)
    print("open g result:", res)
    all_layer_g = job_operation.get_all_layers(job_g_name)
    if len(all_layer_g) == 0:
        g_vs_total_result_flag = False
        print("G-ODB++打开失败！！！！！")
    else:
        print('G软件tgz中的层信息：', all_layer_g)

    # 以G转图为主来比对
    job_g_g_path = r'\\vmware-host\Shared Folders\share/{}/g/{}'.format('temp' + "_" + str(job_id) + "_" + vs_time_g,
                                                                        job_g_name)
    # job_g_g_path = r'Z:/share/{}/g/{}'.format('temp' + "_" + str(job_id) + "_" + vs_time_g, job_g_name)
    job_ep_g_path = r'\\vmware-host\Shared Folders\share/{}/ep/{}'.format('temp' + "_" + str(job_id) + "_" + vs_time_g,
                                                                          job_ep_name)
    # job_ep_g_path = r'Z:/share/{}/ep/{}'.format('temp' + "_" + str(job_id) + "_" + vs_time_g,job_ep_name)
    # 读取配置文件
    with open(r'C:\cc\python\epwork\epcam_test_client\config_g\config.json', encoding='utf-8') as f:
        cfg = json.load(f)
    tol = cfg['job_manage']['vs']['vs_tol_g']
    print("tol:", tol)
    map_layer_res = 200
    print("job1:", job_g_name, "job2:", job_ep_name)

    # 导入要比图的资料
    print("job_g_g_path:", job_g_g_path, Path(job_g_g_path))
    asw.import_odb_folder(job_g_g_path)
    asw.import_odb_folder(job_ep_g_path)
    # G打开要比图的2个料号
    job_g_name = job_g_name.lower()
    job_ep_name = job_ep_name.lower()
    asw.layer_compare_g_open_2_job(job1=job_g_name, step='orig', job2=job_ep_name)
    g_compare_result_folder = 'g_compare_result'
    temp_g_compare_result_path = os.path.join(temp_path, g_compare_result_folder)
    if not os.path.exists(temp_g_compare_result_path):
        os.mkdir(temp_g_compare_result_path)
    temp_path_remote_g_compare_result = r'//vmware-host/Shared Folders/share/{}/{}'.format(
        'temp' + "_" + str(job_id) + "_" + vs_time_g, g_compare_result_folder)
    temp_path_local_g_compare_result = os.path.join(temp_path, g_compare_result_folder)

    all_result_g = {}
    for layer in all_layer_g:
        # print("g_layer:", layer)
        if layer in all_layer_ep:
            map_layer = layer + '-com'
            result = asw.layer_compare_one_layer(job1=job_g_name, step1='orig', layer1=layer, job2=job_ep_name,
                                                 step2='orig', layer2=layer, layer2_ext='_copy', tol=tol,
                                                 map_layer=map_layer, map_layer_res=map_layer_res,
                                                 result_path_remote=temp_path_remote_g_compare_result,
                                                 result_path_local=temp_path_local_g_compare_result,
                                                 temp_path=temp_path)
            all_result_g[layer] = result
            if result != "正常":
                g_vs_total_result_flag = False
        else:
            pass
            print("悦谱转图中没有此层")
    asw.save_job(job_g_name)
    asw.save_job(job_ep_name)
    asw.layer_compare_close_job(job1=job_g_name, job2=job_ep_name)

    # 开始查看比对结果
    # 获取原始层文件信息，最全的
    all_layer_from_org = [each for each in DMS().get_job_layer_fields_from_dms_db_pandas(job_id, field='layer_org')]
    all_result = {}  # all_result存放原始文件中所有层的比对信息
    for layer_org in all_layer_from_org:
        layer_org_find_flag = False
        layer_org_vs_value = ''
        for each_layer_g_result in all_result_g:
            if each_layer_g_result == str(layer_org).lower().replace(" ", "-").replace("(", "-").replace(")", "-"):
                layer_org_find_flag = True
                layer_org_vs_value = all_result_g[each_layer_g_result]
        if layer_org_find_flag == True:
            all_result[layer_org] = layer_org_vs_value
        else:
            all_result[layer_org] = 'G转图中无此层'

    data["all_result_g"] = all_result_g
    data["all_result"] = all_result



    Print.print_with_delimiter('比对结果信息展示--开始')
    if g_vs_total_result_flag == True:
        print("恭喜您！料号导入比对通过！")
        # print("\033[1;32m 字体颜色：深黄色\033[0m")
    if g_vs_total_result_flag == False:
        print("Sorry！料号导入比对未通过，请人工检查！")
    Print.print_with_delimiter('分割线', sign='-')
    print('G转图的层：', all_result_g)
    Print.print_with_delimiter('分割线', sign='-')
    print('所有层：', all_result)
    Print.print_with_delimiter('比对结果信息展示--结束')

    return data



if __name__ == "__main__":
    pass
    import argparse
    parser = argparse.ArgumentParser(description='manual to this script')
    parser.add_argument('--int_job_id', type=int, default=None)
    args = parser.parse_args()
    print("int_job_id:",args.int_job_id)

    # data = vs_g(2521)
    data=vs_g(args.int_job_id)

    print("输入'g'退出窗口！\n输入's'提交比对结果！")
    exit_input=input()
    if exit_input =="q":
        exit()

    elif exit_input =="s":
        pass
        print("开始发送比对结果到DMS！")

        session = requests.session()

        response = session.post("http://10.97.80.119/job_manage/send_vs_g_local_result", json=json.dumps(data,ensure_ascii=False))  # post请求
        print(response)
        print(response.text)

        time.sleep(1000)



