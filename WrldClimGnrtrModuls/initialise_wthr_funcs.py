"""
#-------------------------------------------------------------------------------
# Name:        initialise_funcs.py
# Purpose:     script to read and write the setup and configuration files
# Author:      Mike Martin
# Created:     31/07/2015
# Licence:     <your licence>
#-------------------------------------------------------------------------------
"""
__prog__ = 'initialise_funcs.py'
__version__ = '0.0.0'

# Version history
# ---------------
# 
from os.path import join, normpath, exists, isfile, isdir, split, splitext, splitdrive
from os import makedirs, getcwd, name as os_name
from json import load as json_load, dump as json_dump
from json.decoder import JSONDecodeError
from glob import glob
from time import sleep
from sys import exit
from pandas import read_excel
from xlrd import XLRDError
from PyQt5.QtWidgets import QApplication

from set_up_logging import set_up_logging
from glbl_ecss_cmmn_cmpntsGUI import print_resource_locations
from glbl_ecsse_low_level_fns import check_cultiv_json_fname, check_rotation_json_fname
from shape_funcs import format_bbox, calculate_area
from weather_datasets_ltd_data import change_weather_resource, record_weather_settings
from hwsd_bil import check_hwsd_integrity
from hwsd_mu_globals_fns import HWSD_mu_globals_csv
from mngmnt_fns_and_class import ManagementSet

APPLIC_STR = 'glbl_ecss_site_spec_sv'
ERROR_STR = '*** Error *** '
WARNING_STR = '*** Warning *** '

MAX_COUNTRIES = 350

RUN_SETTINGS_SETUP_LIST = ['completed_max', 'check_space_every', 'kml_flag', 'last_gcm_only_flag',
                                'max_countries', 'space_remaining_limit', 'soil_test_flag', 'zeros_file']

SETTINGS_SETUP_LIST = ['config_dir', 'fname_png', 'log_dir', 'n_inputs_xls', 'proj_path', 'regions_fname',
                       'sims_dir', 'weather_dir', 'shp_dir', 'shp_dir_gadm', 'python_exe', 'runsites_py',
                       'weather_resource', 'wthr_prj_dir']

MIN_GUI_SUBLIST = ['autoRunEcFlag', 'cultivJsonFname', 'daily_mode', 'manureFlag',
                                                 'rotaJsonFname', 'rotationFlag', 'perenCrops', 'autoRunEcFlag']
MIN_GUI_LIST = ['strt1801Flag', 'bbox', 'regionIndx', 'yearFrom', 'wthrRsrce', 'maxCells', 'allRegionsFlag']

CMN_GUI_LIST = ['cruStrtYr', 'cruEndYr', 'climScnr', 'futStrtYr', 'futEndYr', 'cropIndx', 'gridResol', 'eqilMode']

ROTHC_KEYS = ['prjDir', 'outDir',  'simStrtYr', 'simEndYr', 'readAllWthrFlag', 'hwsdCsvFname', 'useHwsdFlag']

sleepTime = 5

def _write_dflt_wthr_config_file(config_file):
    """
    ll_lon,    ll_lat  ur_lon,ur_lat
    stanza if config_file needs to be created
    """
    bbox_default = [0, 0, 0, 0]
    _default_config = {
        'minGUI': {
            'strt1801Flag': False,
            'bbox': bbox_default,
            'cultivJsonFname': '',
            'daily_mode': True,
            "manureFlag": False,
            "regionIndx": 0,
            "wthrRsrce": ''
        },
        'cmnGUI': {
            'climScnr': 0,
            'cropIndx': 0,
            'cruStrtYr': 0,
            'cruEndYr': 0,
            'eqilMode': 9.5,
            'futStrtYr': 0,
            'futEndYr': 0,
            'gridResol': 0
        }
    }
    # if config file does not exist then create it...
    with open(config_file, 'w') as fconfig:
        json_dump(_default_config, fconfig, indent=2, sort_keys=True)
        return _default_config

def read_wthr_config_file(form):
    """
    read widget settings used in the previous programme session from the config file, if it exists,
    or create config file using default settings if config file does not exist
    """
    config_file = join(form.setup['root_dir_user'], 'config', 'glbl_ecss_site_spec_wthr_sv.json')
    if exists(config_file):
        try:
            with open(config_file, 'r') as fconfig:
                config = json_load(fconfig)
                print('Read config file ' + config_file)
        except (OSError, IOError, JSONDecodeError) as err:
            print(ERROR_STR + str(err) + ' in config file:\t' + config_file)
            return False
    else:
        config = _write_dflt_wthr_cnfg_file(config_file)
        print('Wrote configuration file ' + config_file)

    grp = 'minGUI'
    for key in MIN_GUI_LIST +  ROTHC_KEYS:
        if key not in config[grp]:
            if key in ROTHC_KEYS:
                if key == 'useHwsdFlag':
                    config[grp][key] = True
                else:
                    config[grp][key] = None
            else:
                mess = ERROR_STR + 'attribute {} required for group {} '.format(key, grp)
                print(mess + 'in config file:\n\t{}'.format(config_file))
                sleep(sleepTime)
                exit(0)

    # reset widgets associated with the HWSD file
    # ===========================================
    hwsd_csv_fname = config[grp]['hwsdCsvFname']
    if hwsd_csv_fname is None:
        print(WARNING_STR + 'HWSD csv file is None')
        hwsd_csv_fname = ''
    elif hwsd_csv_fname != '':
        if isfile(hwsd_csv_fname):
            # read CSV file using pandas and create obj
            # =========================================
            form.hwsd_mu_globals = HWSD_mu_globals_csv(form, hwsd_csv_fname)
            form.w_hwsd_bbox.setText(form.hwsd_mu_globals.aoi_label)
        else:
            print(WARNING_STR + 'HWSD csv file ' + hwsd_csv_fname + ' does not exist')

    if hwsd_csv_fname == '':
        form.hwsd_mu_globals = None
        form.w_hwsd_bbox.setText('')

    form.w_hwsd_fn.setText(hwsd_csv_fname)

    # =================
    prj_dir = config[grp]['prjDir']
    form.w_prj_dir.setText(prj_dir)
    form.setup['prj_dir'] = prj_dir
    form.setup['out_dir'] = join(prj_dir, 'outputs')

    form.w_out_dir.setText(config[grp]['outDir'])
    form.w_sim_strt_yr.setText(str(config[grp]['simStrtYr']))
    form.w_sim_end_yr.setText(str(config[grp]['simEndYr']))

    strt_1801_flag = config[grp]['strt1801Flag']
    read_all_flag = config[grp]['readAllWthrFlag']
    form.setup['bbox'] = config[grp]['bbox']

    max_cells = config[grp]['maxCells']
    all_regions = config[grp]['allRegionsFlag']
    yr_from = config[grp]['yearFrom']
    form.w_combo00a.setCurrentIndex(config[grp]['regionIndx'])

    use_hwsd_flag = config[grp]['useHwsdFlag']

    wthr_rsrce = config[grp]['wthrRsrce']
    wthr_rsrce_indx = form.w_combo10w.findText(str(wthr_rsrce))
    if wthr_rsrce_indx == -1:
        wthr_rsrce = 'CRU'  # default

    nitems = form.w_combo10w.count()
    if 0 <= wthr_rsrce_indx < nitems:
        form.w_combo10w.setCurrentText(wthr_rsrce)

    wthr_rsrce = form.w_combo10w.currentText()
    change_weather_resource(form, wthr_rsrce)

    # common area
    # ===========
    grp = 'cmnGUI'
    for key in config[grp]:
        if key not in CMN_GUI_LIST:
            print(ERROR_STR + 'attribute {} required for group {} in config file {}'.format(key, grp, config_file))
            sleep(sleepTime)
            exit(0)

    scenario = str(config[grp]['climScnr'])
    hist_strt_year = config[grp]['cruStrtYr']
    hist_end_year = config[grp]['cruEndYr']
    sim_strt_year = config[grp]['futStrtYr']
    sim_end_year = config[grp]['futEndYr']

    form.w_combo09s.setCurrentIndex(hist_strt_year)
    form.w_combo09e.setCurrentIndex(hist_end_year)
    form.w_combo10.setCurrentText(scenario)
    form.w_combo11s.setCurrentIndex(sim_strt_year)
    form.w_combo11e.setCurrentIndex(sim_end_year)

    nitems = form.w_combo11e.count()
    form.w_combo11e.setCurrentIndex(nitems - 1)

    form.w_combo16.setCurrentIndex(config[grp]['gridResol'])

    # record weather settings
    # =======================
    form.wthr_settings_prev[wthr_rsrce] = record_weather_settings(scenario, hist_strt_year, hist_end_year,
                                                                            sim_strt_year, sim_end_year)
    # bounding box set up
    # ===================
    area = calculate_area(form.setup['bbox'])
    ll_lon, ll_lat, ur_lon, ur_lat = form.setup['bbox']
    form.w_ll_lon.setText(str(ll_lon))
    form.w_ll_lat.setText(str(ll_lat))
    form.w_ur_lon.setText(str(ur_lon))
    form.w_ur_lat.setText(str(ur_lat))
    form.lbl03.setText(format_bbox(form.setup['bbox'], area))
    form.bbox = form.setup['bbox']  # legacy

    form.w_max_cells.setText(str(max_cells))
    form.w_yr_from.setText(str(yr_from))

    # set check boxes
    # ===============
    if use_hwsd_flag:
        form.w_use_hwsd_fn.setCheckState(2)
    else:
        form.w_use_hwsd_fn.setCheckState(0)

    if all_regions:
        form.w_all_regions.setCheckState(2)
    else:
        form.w_all_regions.setCheckState(0)

    if strt_1801_flag:
        form.w_strt_1801.setCheckState(2)
    else:
        form.w_strt_1801.setCheckState(0)

    if read_all_flag:
        form.w_read_all.setCheckState(2)
    else:
        form.w_read_all.setCheckState(0)

    return True

def _write_dflt_wthr_cnfg_file(config_file):
    """
    ll_lon,    ll_lat  ur_lon,ur_lat
    stanza if config_file needs to be created
    """
    bbox_default = [0, 0, 0, 0]
    _default_config = {
        'minGUI': {
            'allRegionsFlag': False,
            'readAllWthrFlag': False,
            'strt1801Flag': False,
            'bbox': bbox_default,
            'outDir': 0,
            'simStrtYr': 0,
            'simEndYr': 0,
            'daily_mode': True,
            'maxCells': 0,
            'regionIndx': 0,
            'prjDir': '',
            'wthrRsrce': '',
            'yearFrom': ''
        },
        'cmnGUI': {
            'climScnr': 0,
            'cropIndx': 0,
            'cruStrtYr': 0,
            'cruEndYr': 0,
            'futStrtYr': 0,
            'futEndYr': 0,
            'gridResol': 0
        }
    }
    # if config file does not exist then create it...
    with open(config_file, 'w') as fconfig:
        json_dump(_default_config, fconfig, indent=2, sort_keys=True)
        return _default_config

def write_wthr_config_file(form):
    """
    write current selections to config file
    """

    # facilitate multiple config file choices
    # =======================================
    applic_str = form.setup['applic_str']
    config_file = join(form.setup['root_dir_user'], 'config', 'glbl_ecss_site_spec_wthr_sv.json')

    # prepare the bounding box
    # ========================
    try:
        ll_lon = float(form.w_ll_lon.text())
        ll_lat = float(form.w_ll_lat.text())
        ur_lon = float(form.w_ur_lon.text())
        ur_lat = float(form.w_ur_lat.text())
    except ValueError:
        ll_lon = 0.0
        ll_lat = 0.0
        ur_lon = 0.0
        ur_lat = 0.0
    form.setup['bbox'] = list([ll_lon, ll_lat, ur_lon, ur_lat])

    sim_strt_yr = form.w_sim_strt_yr.text()
    sim_end_yr = form.w_sim_end_yr.text()

    config = {
        'cmnGUI': {
            'cruStrtYr': form.w_combo09s.currentIndex(),
            'cruEndYr': form.w_combo09e.currentIndex(),
            'climScnr': form.w_combo10.currentText(),
            'futStrtYr': form.w_combo11s.currentIndex(),
            'futEndYr': form.w_combo11e.currentIndex(),
            'gridResol': form.w_combo16.currentIndex()
        },
        'minGUI': {
            'allRegionsFlag': form.w_all_regions.isChecked(),
            'readAllWthrFlag': form.w_read_all.isChecked(),
            'strt1801Flag': form.w_strt_1801.isChecked(),
            'autoRunEcFlag': form.w_auto_run_ec.isChecked(),
            'prjDir': form.w_prj_dir.text(),
            'bbox': form.setup['bbox'],
            'useHwsdFlag': form.w_use_hwsd_fn.isChecked(),
            'hwsdCsvFname': form.w_hwsd_fn.text(),
            'maxCells': form.w_max_cells.text(),
            'outDir': form.w_out_dir.text(),
            'simStrtYr': sim_strt_yr,
            'simEndYr': sim_end_yr,
            'yearFrom': form.w_yr_from.text(),
            'regionIndx': form.w_combo00a.currentIndex(),
            'wthrRsrce': form.w_combo10w.currentText()
        }
    }
    if isfile(config_file):
        descriptor = 'Overwrote existing'
    else:
        descriptor = 'Wrote new'

    with open(config_file, 'w') as fconfig:
        try:
            json_dump(config, fconfig, indent=2, sort_keys=True)
            print('\n' + descriptor + ' configuration file ' + config_file)
        except BaseException as err:
            print(str(err))

    return
