"""
1. Open an irrelevant file in Guitar Pro 
2. Put the Guitar Pro window on laptop screen
3. Double click the window to make sure it fits the screen
4. Run this directly in VSCode
5. After finishing the FILE_COUNT files, go to finder and move the finished files to another directory

When measuring mouse position on the screen, run `pyautogui.position()` in terminal
Use ctrl + ` to toggle focus between editor and terminal
"""
import pyautogui
import time

pyautogui.PAUSE = 1
pyautogui.FAILSAFE = True

# how many files to export
FILE_COUNT = 30

for i in range(FILE_COUNT):
    # click on gtp window
    pyautogui.moveTo(x=407, y=37, duration=0.5)
    pyautogui.click()
    # open file
    pyautogui.hotkey("command", "o")
    time.sleep(3)
    # down button multiple times to locate different files
    # the n-th file requires n downs
    # sometimes GuitarPro software doesn't respond to down button, just stop and try again several times
    for j in range(i + 1):
        pyautogui.typewrite(["down"])

    # confirm open file
    pyautogui.typewrite(["enter"])
    time.sleep(1)

    # file
    pyautogui.click(x=168, y=14, duration=0.5)
    # export
    pyautogui.moveTo(x=179, y=350, duration=0.5)
    # audio
    pyautogui.click(x=408, y=483, duration=0.1)
    # confirm export
    pyautogui.click(x=880, y=654, duration=0.5)

    # change dir
    pyautogui.click(x=738, y=255, duration=0.5)
    pyautogui.click(x=738, y=282, duration=0.5)

    # double click somehow doesn't work, this is the alternative
    pyautogui.click(x=738, y=334, duration=0.5)
    pyautogui.typewrite(["enter"])

    time.sleep(2)

    # click on save
    pyautogui.moveTo(1118, 548, duration=0.5)
    pyautogui.click()

    # uncheck "open dir when export is done"
    pyautogui.click(x=598, y=489, duration=0.5)

    # wait for file to export
    print(f"{i+1} / {FILE_COUNT}")
    # 26 seconds is arbitary, a 10-minute song took around 22s to export
    time.sleep(26)

    # close the file, so that we don't end up with a thousand tabs in guitar pro
    pyautogui.click(x=1407, y=115, duration=0.5)
