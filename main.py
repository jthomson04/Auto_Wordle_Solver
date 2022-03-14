from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from time import sleep
from itertools import chain
from math import log2
from itertools import product
import datetime
from tqdm import tqdm
import requests
import ast
from copy import deepcopy
import bisect


class WordleSolver:
    class Cell:
        def __init__(self, elem=None, state=None, letter=None):
            if elem is not None:
                self.letter = elem.get_attribute("innerHTML")
                self.state = elem.get_attribute("data-state")
            else:
                self.letter = letter
                self.state = state

        def __str__(self):
            return f"{self.letter}: {self.state}"

    @staticmethod
    def download_words():
        web_content = requests.get('https://www.nytimes.com/games/wordle/main.4d41d2be.js').text
        beg_1 = web_content.index("Oa")
        start_index_1 = web_content.index("[", beg_1)
        end_index_1 = web_content.index("]", beg_1)

        beg_2 = web_content.index("var Ma")

        start_index_2 = web_content.index("[", beg_2)
        end_index_2 = web_content.index("]", beg_2)

        return ast.literal_eval(web_content[start_index_1:end_index_1 + 1]) + ast.literal_eval(web_content[start_index_2:end_index_2 + 1])

    def __init__(self):
        self.words = sorted(WordleSolver.download_words())
        self.guess_num = 1
        self.driver = webdriver.Chrome(service=Service("""/Users/johnthomson/Desktop/wordle4.0/chromedriver"""))

    def get_rows(self):
        return [[WordleSolver.Cell(elem=self.driver.execute_script(
            f'return document.querySelector("game-app").shadowRoot.querySelector("game-theme-manager").querySelectorAll("game-row")[{i}].shadowRoot.querySelectorAll("game-tile")[{j}].shadowRoot.querySelector(".tile")')) for j in range(5)]
            for i in range(6)]

    @staticmethod
    def find_in_sorted_list(elem, sorted_list):
        # from https://stackoverflow.com/questions/3196610/searching-a-sorted-list
        i = bisect.bisect_left(sorted_list, elem)
        if i != len(sorted_list) and sorted_list[i] == elem:
            return i
        return -1

    @staticmethod
    def get_potential_wordlist(row, potential_words):
        def map_val(d, key):
            return d[key] if key in d else -1

        reqs = []

        row_req = {}
        for cell in row:
            if cell.state == "absent" and (cell.letter not in row_req or row_req[cell.letter] == 0):
                row_req[cell.letter] = 0
            else:
                if cell.letter in row_req:
                    row_req[cell.letter] += 1
                else:
                    row_req[cell.letter] = 1
        reqs.append(row_req)

        master_reqs = {}
        for letter in "abcdefghijklmnopqrstuvwxyz":
            if any(letter in req for req in reqs):
                master_reqs[letter] = [max(map_val(req, letter) for req in reqs), any(cell.state == "absent" and cell.letter == letter for cell in row)]

        for k in master_reqs.keys():
            potential_words = [word for word in potential_words if
                               (1 <= master_reqs[k][0] <= word.count(k) and not master_reqs[k][1]) or (1 <= master_reqs[k][0] == word.count(k) and master_reqs[k][1]) or (master_reqs[k][0] == 0 and word.count(k) == 0)]

        idx_requirements = {}

        for idx, cell in enumerate(row):
            if cell.state == "correct":
                if cell.letter in idx_requirements:
                    idx_requirements[cell.letter].append(idx)
                else:
                    idx_requirements[cell.letter] = [idx]

        for k in idx_requirements.keys():
            potential_words = [word for word in potential_words if all(word[idx] == k for idx in idx_requirements[k])]

        yellow_exclusions = {}

        for idx, cell in enumerate(row):
            if cell.state == "present":
                if cell.letter in yellow_exclusions:
                    yellow_exclusions[cell.letter].append(idx)
                else:
                    yellow_exclusions[cell.letter] = [idx]

        for k in yellow_exclusions.keys():
            potential_words = [word for word in potential_words if all(word[idx] != k for idx in yellow_exclusions[k])]
        return potential_words

    def select_best_word(self, round, potential_words):

        best_guess = ""
        best_val = -999999999999999999999999999999
        if len(potential_words) == 1 or len(potential_words) == 2:
            return potential_words[0]
        for idx, possible_guess in tqdm(enumerate(self.words), total=len(self.words), unit="word"):
            temp_potential_words = deepcopy(potential_words)
            vals = []
            for output_seq in product(["absent", "present", "correct"], repeat=5):
                row = [WordleSolver.Cell(state=state, letter=letter) for state, letter in zip(output_seq, possible_guess)]
                new_potential_words = WordleSolver.get_potential_wordlist(row, temp_potential_words)
                vals.append(len(new_potential_words) / len(potential_words))

                for word in new_potential_words:
                    temp_potential_words.pop(WordleSolver.find_in_sorted_list(word, temp_potential_words))
                if len(temp_potential_words) == 0:
                    break
            val = -sum([log2(x) * x for x in vals if x != 0])

            if val > best_val:
                best_val = val
                best_guess = possible_guess
        return best_guess

    def play(self):

        self.driver.get("https://www.nytimes.com/games/wordle/index.html")
        sleep(1)
        body = self.driver.find_element(By.TAG_NAME, "body")
        body.click()
        sleep(1)
        potential_words = deepcopy(self.words)
        for round in range(6):

            if round != 0 and all(cell.state == "correct" for cell in self.get_rows()[round - 1]):
                print("yeet")
                exit()

            if round != 0:
                potential_words = self.get_potential_wordlist(self.get_rows()[round - 1], potential_words)
                print(f"Possible Words: {len(potential_words)}")
            if round == 0:
                guess = "soare"
            else:
                guess = self.select_best_word(round, potential_words)

            for i in range(5):
                body.send_keys(guess[i])
                sleep(0.25)
            body.send_keys(Keys.RETURN)
            sleep(1.5)

wordle = WordleSolver()
wordle.play()
