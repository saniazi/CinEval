from multiprocessing import freeze_support

from cinevalmulti import CinEval

def main():
    #Support for frozen executable and prevents multiple instances of
    #GUI opening
    freeze_support()
    
    app = CinEval()
    app.mainloop()
    
if __name__ == '__main__':
    main()