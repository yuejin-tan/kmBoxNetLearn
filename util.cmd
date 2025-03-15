pyuic5 cs2GG.ui -o cs2GG_ui.py

@REM 新建环境

conda remove -n xxxxx(名字) --all

conda update -n base -c defaults conda

conda create -n can_dev

conda activate can_dev

conda install python

pip install pyqt5 numpy scipy matplotlib canlib pyinstaller pyqt5-tools pyqt5-stubs autopep8 keyboard
