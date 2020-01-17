''' Copyright © 2019 Shakeel Niazi

This module is a modification of the original cineval module which
uses multiprocessing for the CinEval class to achieve better
performance in retrieving ratings.

CinEval lets you browse through movies with their ratings.
Ratings include critics ratings (Tomatometer) and audience
ratings.  

@author: Shakeel Niazi
'''
import os
import sys
import webbrowser
import time
import datetime as dtime
from multiprocessing import Pool, freeze_support
from datetime import datetime
from sys import platform

import requests
import tkinter as tk
from tkinter import ttk, font
from bs4 import BeautifulSoup
from unidecode import unidecode
from PIL import Image, ImageTk
from ttkthemes import themed_tk as themed


class CinEval(themed.ThemedTk):
    '''CinEval creates a themed tk GUI that lets users browse movies
    and their ratings.
    
    Class Attributes:
        WIN_W: window width
        WIN_H: window height
    '''
    WIN_W = 950
    WIN_H = 500
    
    _MONTHS = ['All', 'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November',
                'December']
    _HEADERS = ['Release Date', 'Title', 'Distributor', 'Domestic Sales',
               'Tomatometer', 'Audience Score']
    _AMBIG_RELEASES = ['Spring', 'Summer', 'Fall', 'Winter', 'During', 'TBD']
    
    _FONT = ('Calibri', 13)
    _WINDOW_SIZE = '%dx%d' % (WIN_W, WIN_H)
    _CANV_H = WIN_H - 170 
    _CANV_W = WIN_W - 100
    _IMAGE_NAME = 'popcorn.jpg'
    
    
    def __init__(self):
        '''Constructs a themed tk GUI for retrieving lists of movies
        and their ratings.
        
        Provides options to browse movies by their theatrical or home
        media release dates. Also provides the ability to view their
        summaries on the-numbers.com by double clicking them. Double
        clicking on their ratings will let you view their summaries on
        Rotten Tomatoes.
        
        '''
        themed.ThemedTk.__init__(self)
        self.set_theme('black')
        self.title('CinEval')
        self.geometry(CinEval._WINDOW_SIZE)
        self.container = tk.Frame(self, bg='black')
        
        try:
            #Pyinstaller stores path in temp folder _MEIPASS
            self.filename = os.path.join(sys._MEIPASS, CinEval._IMAGE_NAME)
        except AttributeError:
            self.filename = CinEval._IMAGE_NAME
            
        self.image = Image.open(self.filename)
        self.bg_img = ImageTk.PhotoImage(self.image)
        self.bg_label = tk.Label(self.container, image=self.bg_img)
        
        self.canvas = tk.Canvas(self.container, width=CinEval._CANV_W,
                                height=CinEval._CANV_H, bg='#262626', 
                                bd=0, highlightthickness=0, relief='ridge')
        self.options_frame = tk.Frame(self.canvas, bg='#262626', bd=0)
        self.results_box = ttk.Treeview(self.options_frame,
                                        columns=CinEval._HEADERS,
                                        show='headings')
        self.no_results = ttk.Label(self.options_frame, text='No results.',
                                    font=CinEval._FONT)
        self.no_selection = ttk.Label(self.options_frame,
                                      text='Please select a movie first.',
                                      font=CinEval._FONT)
        
        self._set_up_canvas()
        self._set_up_options()
        self._set_up_results_box()
        self._bind_mousewheel()
        
        self.container.pack(fill='both', expand=True)
        self.container.rowconfigure(index=0, weight=1)
        self.container.columnconfigure(index=0, weight=1)
        
        style = ttk.Style()
        style.configure('cust.Treeview.Heading', font=CinEval._FONT)
        style.configure('cust.Treeview', rowheight=30)
        self.results_box.config(style='cust.Treeview')
        
        self.bg_label.grid(row=0, column=0)
        padx = (CinEval.WIN_W - CinEval._CANV_W)/2.0
        self.canvas.grid(row=0, column=0, sticky='we', padx=padx)
        self.no_results.grid(row=1, column=0, columnspan=9)
        self.no_selection.grid(row=1, column=0, columnspan=9)
        self.results_box.grid(row=1, column=0, columnspan=9, sticky='nesw',
                              pady=10)
        self.results_box.tkraise()
        
        self.row_info = {}
        
    def _set_up_canvas(self):
        #Sets up the canvas which will contain the frame containing
        #the options bar and display area for results
        
        #Scrollbars for main window are created
        self.main_vscroll = tk.Scrollbar(self.container,
                                         command=self.canvas.yview)
        self.main_hscroll = tk.Scrollbar(self.container, orient='horizontal',
                                     command=self.canvas.xview)
        self.canvas.config(yscrollcommand=self.main_vscroll.set, 
                      xscrollcommand=self.main_hscroll.set)
        
        
        self.canvas.create_window((0,0), window=self.options_frame,
                                  anchor='nw', height=CinEval._CANV_H,
                                  width=CinEval._CANV_W, 
                                  tag='options_frame')        
        
    def _set_up_options(self):
        #Sets up the options bar containing months option, search
        #option, year entry, search button and get rating button.
        
        display_values = ['Theatrical releases', 'Home media']
        
        #Create custom style for the buttons and labels to change
        #their fonts and colour.
        style = ttk.Style()
        style.configure('cust.TButton', anchor='center',
                        font=CinEval._FONT)
        style.configure('cust.TLabel', background='#262626')
        self.option_add('*TCombobox*Listbox.font', CinEval._FONT)
            
        self.front_space = tk.Label(self.options_frame, bg='#262626')
        self.end_space = tk.Label(self.options_frame, bg='#262626')
        self.search_option = ttk.Combobox(self.options_frame,state='readonly',
                                           values=display_values, width=16,
                                           font=CinEval._FONT)
        self.search_option.current(0)
        self.months_option = ttk.Combobox(self.options_frame,state='readonly',
                                          values=CinEval._MONTHS, width=10,
                                          font=CinEval._FONT)
        self.months_option.current(0)
        self.month_label = ttk.Label(self.options_frame, text=' Month: ',
                                     font=CinEval._FONT,
                                     style='cust.TLabel')
        self.year_label = ttk.Label(self.options_frame, text=' Year: ',
                                    font=CinEval._FONT,
                                    style='cust.TLabel')
        self.year_entry = ttk.Entry(self.options_frame,
                                    font=CinEval._FONT, width=6)
        self.year_entry.bind('<FocusIn>', 
                             lambda event: self.year_entry.bind('<Return>', self._get_results))
        
        self.search_bttn = ttk.Button(self.options_frame, text='Search',
                                      style='cust.TButton',
                                      command=self._get_results) #padx=10
        self.rating_bttn = ttk.Button(self.options_frame, text='Get Ratings',
                                      style='cust.TButton',
                                      command=self._get_ratings)
        
        self.front_space.grid(row=0,column=0)
        self.end_space.grid(row=0, column=8)
        self.search_option.grid(row=0, column=1)
        self.months_option.grid(row=0,column=3)
        self.month_label.grid(row=0,column=2, sticky='nesw')
        self.year_label.grid(row=0,column=4, sticky='nesw')
        self.year_entry.grid(row=0, column=5)
        self.search_bttn.grid(row=0, column=6, padx=10)
        self.rating_bttn.grid(row=0, column=7)
        
        self.bind('<Configure>', self._on_configure)
        self.options_frame.columnconfigure(index=0, weight=1)
        self.options_frame.columnconfigure(index=8, weight=1)
        self.options_frame.rowconfigure(index=1, weight=1)
        
    def _set_up_results_box(self):
        #Sets up the area where results are listed. Uses ttk Treeview
        #to display results. 
        
        for header in CinEval._HEADERS:
            col_w = font.Font(family=CinEval._FONT[0],
                              size=CinEval._FONT[1]).measure(header)
            self.results_box.heading(header, text=header,
                                     command=lambda col=header:
                                        self._sort_column(col, True))
            self.results_box.column(header, width=col_w, minwidth=col_w)
        
        self.result_vscroll = ttk.Scrollbar(self.results_box,
                                            command=self.results_box.yview)
        self.result_hscroll = ttk.Scrollbar(self.results_box,
                                            orient='horizontal',
                                            command=self.results_box.xview)
        
        self.results_box.configure(yscrollcommand=self.result_vscroll.set,
                                   xscrollcommand=self.result_hscroll.set)
        
        self.results_box.bind('<Double-1>', self._on_double)
        self.results_box.bind('<Enter>', self._on_enter)
        
    def _bind_mousewheel(self):
        #Binds mousewheel to scrollable areas. Formatted for different
        #platforms.
        
        if platform == 'linux':
            self.bg_label.bind('<Button-4>',
                               lambda event, arg=-1:self._on_mousewheel(event, arg))
            self.bg_label.bind('<Button-5>',
                               lambda event, arg=1: self._on_mousewheel(event, arg))
        else:
            self.bg_label.bind('<MouseWheel>', self._on_mousewheel)
    
    def _sort_column(self, col, reverse):
        #Sorts columns for displayed results in a ttk Treeview.
        
        results = self.results_box.get_children('')
        
        #Delete the blank last row before commencing if there are
        #results.
        num_results = len(results)
        if num_results > 0:
            self.results_box.delete(results[-1])
            results = results[:-1]
            
        values = [(self.results_box.set(row_id, col), row_id)
                  for row_id in results]
        
        #These four columns need additional formatting when being 
        #sorted.
        date_col = CinEval._HEADERS[0]
        sales_col = CinEval._HEADERS[3]
        tomatometer_col = CinEval._HEADERS[4]
        aud_rating_col = CinEval._HEADERS[5]
        if col == date_col:
            values.sort(key=lambda date: self._format_dates(date[0]),
                        reverse=reverse)
        elif col == sales_col:
            values.sort(reverse=reverse,
                        key=lambda sales: self._format_sales(sales[0]))
        elif col == tomatometer_col or col == aud_rating_col:
            values.sort(reverse=reverse,
                        key=lambda rating: self._format_ratings(rating[0]))
        else:
            values.sort(reverse=reverse)
        
        for i, value in enumerate(values):
            self.results_box.move(value[1], '', i)
        
        #Insert back the blank last row.
        if num_results > 0:
            self.results_box.insert('', 'end')
        
        #Switch the sorting order option to sort in opposite direction
        #next time.
        self.results_box.heading(col,
                                 command=lambda col=col:
                                    self._sort_column(col, not reverse))
        
    def _format_dates(self, date):
        #Returns a datetime object created from given date to assist
        #with sorting
        
        if (not (any(release in date 
                     for release in CinEval._AMBIG_RELEASES))
            and len(date.split()) == 3):
            return datetime.strptime(date, '%B %d, %Y')
        
        return datetime(year=dtime.MINYEAR, month=1, day=1)
    
    def _format_sales(self, sales):
        #Returns sales as a valid int to assist with sorting.
        
        return (int(sales.replace('$', '').replace(',',''))
                if sales != '\xa0' else 0)
    
    def _format_ratings(self, rating):
        #Returns rating as a valid int to assist with sorting.
        
        if (rating != '' and rating != 'Not rated'
            and rating != 'N/A'):
            return int(rating.replace('%',''))
        elif rating == '':
            return -3
        elif rating == 'N/A':
            return -2
        else:
            return -1
                
    def _on_configure(self, event):
        #Resizes canvas and options frame when window is resized.
        
        frame_w = self.options_frame.winfo_width()
        frame_h = self.options_frame.winfo_height()
        region = (0,0, frame_w, frame_h)
        
        win_w = self.container.winfo_width()
        win_h = self.container.winfo_height()
        
        min_w = CinEval.WIN_W
        min_h = CinEval.WIN_H
        
        self.canvas.config(scrollregion = region)

        self.main_vscroll.grid_forget()
        self.main_hscroll.grid_forget()
        
        #Show scrollbars only when scrollable areas are not visible.
        if self._frame_not_visible(frame_h=frame_h):
            self.main_vscroll.grid(row=0, column=1, sticky='ns')
        if self._frame_not_visible(frame_w=frame_w):
            self.main_hscroll.grid(row=1, column=0, sticky='we')
        
        pady = (CinEval.WIN_H - CinEval._CANV_H)/2.0
        if (win_w > min_w and win_h > min_h):
            self.canvas.grid(sticky='nesw', pady=pady)
            canv_w = self.canvas.winfo_width()
            canv_h = self.canvas.winfo_height()
            self.canvas.itemconfig('options_frame', width=canv_w,
                                   height=canv_h)
        elif win_h > min_h:
            self.canvas.grid(sticky='nesw', pady=pady)
            canv_h = self.canvas.winfo_height()
            self.canvas.itemconfig('options_frame', height=canv_h)
        elif win_w > min_w:
            self.canvas.grid(sticky='we', pady=0)
            canv_w = self.canvas.winfo_width()
            self.canvas.itemconfig('options_frame', width=canv_w)
        else:
            self.canvas.grid(sticky='we', pady=0)
    
    def _frame_not_visible(self, frame_w=0, frame_h=0):
        #Checks whether or not area within canvas is visible.
        
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        
        return frame_h > canvas_h or frame_w > canvas_w
    
    def _on_double(self, event):
        #Opens link associated with movie or rating.
        
        selection = self.results_box.selection()
        
        if len(selection) > 0:
            clicked_row = self.results_box.identify_row(event.y)
            if clicked_row in self.row_info:
                col_id = self.results_box.identify_column(event.x)
                
                link = (self.row_info[clicked_row][4]
                        if col_id == '#5' or col_id == '#6'
                        else self.row_info[clicked_row][2])
                
                if link is not None:
                    webbrowser.open(link)
                  
    def _on_enter(self, event):
        #Reveals scrollbars only when results area is not fully
        #visible.
    
        self.result_hscroll.pack_forget()
        self.result_vscroll.pack_forget()
        
        fully_visible = (0.0, 1.0) #position when fully visible
        
        if self.results_box.xview() != fully_visible:
            self.result_hscroll.pack(side='bottom', fill='x')
        
        if self.results_box.yview() != fully_visible:
            self.result_vscroll.pack(side='right', fill='y')
        
    def _on_mousewheel(self, event, scroll=None):
        #Scrolls an area when using the mousewheel
        
        frame_h = self.options_frame.winfo_height()
        
        #Only activate scrolling when options frame not fully visible.
        if self._frame_not_visible(frame_h=frame_h):
            if platform == 'darwin':
                self.canvas.yview_scroll(-1*event.delta, 'units')
            elif platform == 'linux':
                self.canvas.yview_scroll(int(scroll), 'units')
            else:
                self.canvas.yview_scroll(int(-1*(event.delta/120)), 'units')
    
    def _contains_header(self, tag):
        #Checks if tag contains a heading element
        
        return tag.name == 'tr' and tag.find('h3') is not None
        
    def _get_results(self, event=None):
        #Retrieves list of movies for selected options from site
        
        films_url = 'https://www.the-numbers.com/movies/release-schedule'
        home_media_url = ('https://www.the-numbers.com'
                          + '/home-market/release-schedule')
        
        #Delete old results and raise frame above any other frames
        self.results_box.delete(*self.results_box.get_children())
        self.results_box.tkraise()
        
        input_year = self.year_entry.get()
        is_space = not input_year.split()
        
        if input_year != '':
            try:
                input_year = int(input_year)
            except ValueError:
                if not is_space:
                    self.no_results.tkraise()
                    return
            
            if not (is_space or 1901 < input_year < 10000):
                self.no_results.tkraise()
                return
        
        selected_option = self.search_option.current()
        if not is_space:
            input_year = '/' + str(input_year)
                
        url = films_url + input_year if selected_option == 0 \
            else home_media_url + input_year
        url = url.strip()
        
        response = requests.get(url)
        
        if response.status_code != 200:
            self.no_results.tkraise()
            return
        
        response.encoding = 'UTF-8'
        html = BeautifulSoup(response.text, 'html.parser')
        headers = html.find_all(lambda tag: self._contains_header(tag))
        
        if self.months_option.current() == 0:
            months = CinEval._MONTHS[1:]
            self._display_results(headers, months)
        else:
            month = [self.months_option.get()]
            self._display_results(headers, month)
        
    def _display_results(self, month_headers, months):
        #Displays each movie from a given month or months.
        
        self.row_info = {} #Info for each movie will be stored
        
        for header in month_headers:
            if any(month in header.string for month in months):
                self._results_by_month(header)
        
        #Raise no results frame if no results were found
        if not self.row_info:
            self.no_results.tkraise()
        else:
            #Insert a blank row at the end to keep the last result
            #visible when the horizontal scrollbar is active.
            self.results_box.insert('', 'end')
        
    def _results_by_month(self, month_header):
        #Inserts results from under each given month heading into the
        #ttk Treeview (results box).
        
        home_url = 'https://www.the-numbers.com'
        row = month_header.find_next('tr')
        date = ''
        year = ''
        while row is not None and not self._contains_header(row):
            if not 'colspan' in row.find_next('td').attrs:
                if 'id' in row.attrs:
                    date = str(row.find_next('td').string)
                    if not (any(release in date
                                for release in CinEval._AMBIG_RELEASES)):
                        year = row['id'].split('-')[0]
                        date = date + ', ' + year
                    else:
                        year = str(month_header.string).split()[1]
               
                title_tag = row.find_next('td').find_next('td')
                title = title_tag.string
                href = (title_tag.find('a').get('href')
                        if title_tag.find('a') is not None else None)
                distribution = title.next_element
                distributor = title.find_next('td').string
                distributor = (str(distributor.string)
                               if distributor is not None else '')
                box_office = title.find_next('td').find_next('td').string
                title = str(title)
                title_w_dist = title + str(distribution)
                row_tag = title_w_dist.replace(' ', '').replace('\n', '')
                rt_link = None
                
                row_id = self.results_box.insert('', 'end', 
                                                 values=[date, title_w_dist,
                                                         distributor,
                                                         str(box_office)],
                                                 tags=row_tag)
                
                link = self._hyperlink_row(row_tag, home_url, href)
                
                #Store important info into dict
                self.row_info[row_id] = (title, year, link, row_tag, rt_link)
                
                #Resize the title column
                self._resize_column(CinEval._HEADERS[1], title_w_dist)
                
            row = row.find_next('tr')
    
    def _hyperlink_row(self, row_tag, base_url, href):
        #Change the font of the row to make it appear as a hyperlink.
        #Gives row a regular appearance if link is not available.
        #Returns link, which can be None or a url.
        
        if href is not None:
            link = base_url + href
            _font = font.Font(family=CinEval._FONT[0],
              size=CinEval._FONT[1], underline=True)
            fg = '#4dafff'
        else:
            link = href
            _font = font.Font(family=CinEval._FONT[0],
              size=CinEval._FONT[1])
            fg = 'white'
                    
        self.results_box.tag_configure(row_tag, font=_font,
                                       foreground=fg)
        return link
    
    def _resize_column(self, col, text):
        #Resizes a column based on the width of the text given
        
        _font = font.Font(font=CinEval._FONT)
        text_w = _font.measure(text)
        col_w = self.results_box.column(col, width=None)
        if text_w > col_w:
            self.results_box.column(col, width=text_w)
            
    def _get_ratings(self):
        #Gets the critics and audience ratings from Rotten Tomatoes
        
        #start_time = time.time()
        self.results_box.tkraise()
        selection = self.results_box.selection()
        no_results = not len(self.results_box.get_children())
        
        selection_info = [] #Store info (title, year, row id)
        
        #Proceed if a selection was made
        if len(selection) > 0:
            for row_id in selection:
                if row_id in self.row_info:
                    row_info = self.row_info[row_id]
                    title, year = row_info[0], row_info[1]
                    selection_info.append((title, year, row_id))
        elif no_results:
            self.no_selection.tkraise()
            return
        
        #Create number of processes based on cpu count and use
        #processes to search for ratings for each selection
        processes = Pool()
        selection_ratings = processes.map(CinEval._search_ratings,
                                          selection_info)
        processes.terminate()
        processes.join()
        
        #Insert movie ratings in their respective rows
        for selection in selection_ratings:
            critics_rating, aud_rating, rt_link, row_id = selection
            old = self.results_box.item(row_id, 'values')
            self.results_box.item(row_id,
                                  values=[old[0], old[1], old[2],
                                          old[3], critics_rating,
                                          aud_rating])
            self.row_info[row_id] = row_info[:4] + (rt_link,)
        
        #print(time.time() - start_time)
        
    @staticmethod
    def _search_ratings(selection_info):
        #Searches and returns ratings for a movie given its info:
        #(title, year, row id).
        
        rt_url = 'https://www.rottentomatoes.com/m/'
        
        title, year, row_id = selection_info
        
        #Format title for url.
        formatted_title = unidecode(title)
        formatted_title = '_'.join(formatted_title.split())
        
        replace_chars = [':', "'", '.', ',', '!', '?', '%', '$']
        for char in replace_chars:
            formatted_title = formatted_title.replace(char, '')
        formatted_title = formatted_title.replace('&', 'and')
        
        url = rt_url + formatted_title 
        response = requests.get(url) #Try url with the title only.
        if response.status_code != 200:
            title_w_year = formatted_title + '_' + year
            url = rt_url + title_w_year
            response = requests.get(url) #Try with the year.
            if response.status_code != 200:
                previous_year = str(int(year)-1)
                title_prev_year = formatted_title + '_' + previous_year
                url = rt_url + title_prev_year
                response = requests.get(url) #Try with previous year.
                if response.status_code != 200:
                    return ('N/A', 'N/A', None, row_id) #Not found
                
        response.encoding = 'utf-8'
        html = BeautifulSoup(response.text, 'html.parser')
        critics_rating, aud_rating = CinEval._parse_ratings(html)
        
        return (critics_rating, aud_rating, url, row_id)
    
    @staticmethod
    def _parse_ratings(html):
        #Parse given html code for critics and audience ratings.
        
        critics = html.find(class_='mop-ratings-wrap__half')
        aud = html.find(class_='mop-ratings-wrap__half audience-score')
        
        if critics is not None:
            critics_rating = critics.find(class_= 
                                          'mop-ratings-wrap__percentage')
            critics_rating = (str(critics_rating.string).strip()
                              if critics_rating is not None else 'Not rated')
        else:
            critics_rating = 'N/A'
            
        if aud is not None:
            aud_rating = aud.find(class_='mop-ratings-wrap__percentage')
            aud_rating = (str(aud_rating.string).strip()
                          if aud_rating is not None else 'Not rated')
        else:
            aud_rating = 'N/A'
        
        return (critics_rating, aud_rating)
        
if __name__ == '__main__':
    #Support for frozen executable and prevents multiple instances of
    #GUI opening
    freeze_support()
    
    gui = CinEval()
    
    gui.mainloop()

