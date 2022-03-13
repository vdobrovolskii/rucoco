# RuCoCo (Russian Coreference Corpus)

**See below for the English version.**

</br>

В этом репозитории содержатся рабочие материалы для подготовки русскоязычного референциального корпуса.

[Инструкция по разметке кореферентных цепочек](coreference_guidelines.md)

Инструмент для разметки:

    python coref_markup.py

Инструмент слияния разметок:

    python merge.py text_1.json text_2.json --out text_merged.json
    
Инструмент сравнения разметок:

    python diff.py text_1.json text_2.json

### Благодарности
Спасибо нашей замечательной команде аннотаторов:
* Арина Акимова
* Денис Булаев
* [Дарья Власова](https://github.com/Dariavld)
* [Ирина Гусева](https://github.com/irinaguseva)
* Дарья Дьячкова
* [Амина Зиновьева](https://github.com/AminaZi)
* Анастасия Каверина
* Виктория Малафеева
* Юлия Скрипкарь
* Людмила Шляхтина
* [Анжела Шумилова](https://github.com/AngelaShumilova)
* [Нина Юрчук](https://github.com/Satynth)
* [Лиса была здесь](https://github.com/xiaoliska)
* [Мария Уварова](https://github.com/marie-uvarova)


</br>
</br>

This repository contains work materials for an upcoming Russian coreference dataset.

[Coreference guidelines](coreference_guidelines.md)

Markup tool:

    python coref_markup.py

Markup merge tool:

    python merge.py text_1.json text_2.json --out text_merged.json
    
Markup diff tool:

    python diff.py text_1.json text_2.json
    
### Acknowledgements
Many thanks to our amazing annotators' team:
* Arina Akimova
* Denis Bulaev
* Darya Dyachkova
* [Irina Guseva](https://github.com/irinaguseva)
* Anastasiya Kaverina
* Victoria Malafeeva
* Liudmila Shlyakhtina
* [Angela Shumilova](https://github.com/AngelaShumilova)
* Julia Skripkar
* [Daria Vlasova](https://github.com/Dariavld)
* [Nina Yurchuk](https://github.com/Satynth)
* [Amina Zinowyeva](https://github.com/AminaZi)
* [Lisa was here](https://github.com/xiaoliska)
* [Mariya Uvarova](https://github.com/marie-uvarova)
