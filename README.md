# coref-corpus

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
* Денис Булаев
* [Ирина Гусева](https://github.com/irinaguseva)
* Анастасия Каверина
* Виктория Малафеева
* Людмила Шляхтина
* [Анжела Шумилова](https://github.com/AngelaShumilova) 
* [Лиса была здесь](https://github.com/xiaoliska)
* [Дарья Власова](https://github.com/Dariavld)

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
* Denis Bulaev
* [Irina Guseva](https://github.com/irinaguseva)
* Anastasiya Kaverina
* Victoria Malafeeva
* Liudmila Shlyakhtina
* [Angela Shumilova](https://github.com/AngelaShumilova)
* [Lisa was here](https://github.com/xiaoliska)
* [Daria Vlasova](https://github.com/Dariavld)
