# IELTS 词汇语料库资源汇总

基于参考截图中的15本词汇书（2,556-9,768词），以下是可获取的免费/开源词汇数据源，用于扩充你的项目词汇库。

## 一、核心学术词汇表（免费下载）

### 1. Academic Vocabulary List (AVL) - 强烈推荐 ⭐
- **网址**: http://www.academicvocabulary.info/
- **词汇量**: 3,000个核心学术词 + 20,000个COCA学术词汇
- **格式**: Excel (.xlsx)
- **下载地址**:
  - 核心3000词: http://www.academicvocabulary.info/download.asp
  - COCA-Academic: http://www.academicvocabulary.info/x.asp
- **特点**:
  - 按9个学术领域分类频率（Business, Law, Medicine, Science等）
  - 包含词性、词族、频率数据
  - 适合IELTS学术类考试

### 2. Academic Word List (AWL)
- **网址**: https://www.victoria.ac.nz/lals/resources/academicwordlist
- **词汇量**: 570个词族（约3,000个衍生词）
- **创建者**: Averil Coxhead (惠灵顿维多利亚大学)
- **下载**:
  - 主表: https://www.victoria.ac.nz/lals/resources/academicwordlist/AwlHeadwords.txt
  - 完整词族: https://www.victoria.ac.nz/lals/resources/academicwordlist/AwlFamilies.txt
  - 所有形式: https://www.victoria.ac.nz/lals/resources/academicwordlist/AwlAllForms.txt
- **特点**: IELTS学术词汇的黄金标准

### 3. NGSL (New General Service List)
- **网址**: https://www.newgeneralservicelist.org/
- **词汇量**: 2,809个最高频词
- **下载**: https://www.newgeneralservicelist.org/s/NGSL-101-by-sample-sizeq5a.xlsx
- **特点**: 基础词汇，适合IELTS入门

---

## 二、IELTS专项词汇资源

### 4. IELTS Band 7-9 高频词汇
- **资源**: Quizlet IELTS词汇集
- **网址**: https://quizlet.com/subject/ielts-vocabulary/
- **获取方式**: 使用Quizlet API或导出功能
- **内容**: 多个用户创建的IELTS词汇集

### 5. 剑桥雅思真题词汇 (剑4-19)
- **GitHub资源**:
  - https://github.com/search?q=ielts+vocabulary+list&type=repositories
  - https://github.com/search?q=cambridge+ielts+words&type=repositories
- **建议搜索关键词**:
  - "cambridge ielts vocabulary"
  - "ielts listening vocabulary"
  - "ielts reading vocabulary"

### 6. IELTS话题分类词汇
- **IELTS Mentor**: https://www.ielts-mentor.com/vocabulary
- **IELTS Liz**: https://ieltsliz.com/ielts-vocabulary/
- **IELTS Advantage**: https://www.ieltsadvantage.com/vocabulary/

---

## 三、基础核心词汇表

### 7. Oxford 3000
- **词汇量**: 3,000个核心英语词
- **来源**: 牛津词典基于语料库
- **获取**: https://www.oxfordlearnersdictionaries.com/wordlists/oxford3000/Oxford3000.txt
- **特点**: 最权威的英语核心词汇表

### 8. Longman Communication 3000
- **词汇量**: 3,000个最高频词
- **来源**: Longman语料库
- **获取**: https://www.ldoceonline.com/dictionary/ (需提取)
- **特点**: 区分口语和书面语频率

### 9. General Service List (GSL)
- **词汇量**: 2,000个基础词
- **下载**: https://en.wikipedia.org/wiki/General_Service_List
- **特点**: 英语学习者必备基础词汇

---

## 四、语料库资源

### 10. COCA (Corpus of Contemporary American English)
- **网址**: https://www.english-corpora.org/coca/
- **词汇量**: 10亿词，12万学术词汇
- **特点**:
  - 可按学术子语料库提取
  - 提供频率、搭配、词族数据
- **获取方式**: 注册后可下载词汇列表

### 11. British National Corpus (BNC)
- **网址**: https://www.english-corpora.org/bnc/
- **特点**: 英式英语，适合IELTS英国考试背景

---

## 五、词典API（用于词汇扩充）

### 12. Free Dictionary API
- **文档**: https://dictionaryapi.dev/
- **用途**: 获取音标、定义、发音、例句
- **示例**:
```javascript
fetch('https://api.dictionaryapi.dev/api/v2/entries/en/hello')
```

### 13. Datamuse API
- **文档**: https://www.datamuse.com/api/
- **用途**: 同义词、反义词、相关词
- **特点**: 无API Key，免费使用

### 14. WordsAPI
- **网址**: https://www.wordsapi.com/
- **免费额度**: 2,500 requests/day
- **特点**: 完整的词汇信息（定义、同义词、发音等）

---

## 六、推荐的词汇书结构（匹配参考截图）

基于参考截图中的15本书，建议你的项目按以下分类组织：

| 分类 | 建议词汇量 | 数据来源组合 |
|------|-----------|-------------|
| **听力高频词** | 3,000-4,000 | Oxford 3000 + IELTS真题听力词汇 |
| **阅读高频词** | 3,000-4,000 | AWL + AVL核心词 |
| **核心学术词** | 3,000-4,000 | AVL 3,000 + COCA学术高频 |
| **综合语料库** | 5,000-6,000 | COCA学术子集 + Oxford 3000 |
| **真题词汇** | 8,000-10,000 | 模拟剑4-19真题词汇 |
| **词以类记** | 4,000-5,000 | AVL按领域分类 + 话题分类词 |
| **词组必备** | 1,000-1,500 | 常见搭配、习语 |
| **数字日期地址** | 200-300 | 专项训练词汇 |
| **听力答案词** | 500-700 | 高频拼写词 |

---

## 七、数据格式建议

### JSON结构示例
```json
{
  "word": "analyze",
  "phonetic": "/ˈænəlaɪz/",
  "translation": "分析，研究",
  "pos": "verb",
  "level": "IELTS-7",
  "category": "academic",
  "domain": "science",
  "frequency": 1250,
  "example": "We need to analyze the data carefully."
}
```

### 推荐字段
- `word`: 单词本身
- `phonetic`: 音标
- `translation`: 中文释义
- `pos`: 词性 (noun/verb/adj/adv)
- `level`: IELTS难度等级 (5/6/7/8/9)
- `category`: 分类 (listening/reading/writing/speaking)
- `domain`: 学术领域 (business/medical/science等)
- `frequency`: 出现频率
- `example`: 例句
- `audio_url`: 发音URL

---

## 八、实施步骤

### Phase 1: 基础词汇 (1-2周)
1. 下载 AVL 3000核心词 Excel
2. 下载 AWL 570词族
3. 合并去重，生成基础学术词汇表 (~4,000词)

### Phase 2: 扩充词汇 (2-3周)
1. 下载 Oxford 3000
2. 下载 COCA学术子集前10,000词
3. 按频率筛选IELTS相关词
4. 添加词性、释义信息

### Phase 3: 分类整理 (2周)
1. 按听力/阅读/写作/口语分类
2. 按学术领域分类 (AVL已有)
3. 按难度等级标注
4. 添加例句和发音

### Phase 4: 动态扩充
1. 集成Free Dictionary API自动获取释义
2. 使用Datamuse API添加同义词
3. 用户贡献词汇收集

---

## 九、快速开始脚本

### Python下载脚本示例

```python
import requests
import pandas as pd

# 下载AVL词汇
def download_avl():
    url = "http://www.academicvocabulary.info/x.asp"
    # 使用requests下载Excel文件
    response = requests.get(url)
    with open('avl_3000.xlsx', 'wb') as f:
        f.write(response.content)

    # 读取Excel
    df = pd.read_excel('avl_3000.xlsx')
    return df

# 转换为JSON格式
def convert_to_json(df):
    vocab_list = []
    for _, row in df.iterrows():
        vocab_list.append({
            "word": row['word'],
            "pos": row['pos'],
            "frequency": row['frequency']
        })
    return vocab_list

if __name__ == "__main__":
    df = download_avl()
    vocab_json = convert_to_json(df)
    print(f"下载了 {len(vocab_json)} 个词汇")
```

---

## 十、版权说明

**可自由使用的资源**:
- AVL (academicvocabulary.info) - 学术研究用途免费
- AWL - 学术研究用途免费
- COCA数据 - 需注册，学术用途
- Oxford 3000 - 公开列表

**注意事项**:
- 剑桥雅思真题词汇 - 仅供学习使用，不可商用
- 商业词汇书内容 - 需获得授权
- 建议结合多个免费资源创建原创内容

---

**总计可用词汇**: 通过上述资源可获取 **50,000+** 个带频率数据的学术词汇，远超参考截图中任何一本词汇书的内容量。

**推荐优先级**:
1. ⭐⭐⭐ AVL 3000 (核心学术词)
2. ⭐⭐⭐ AWL 570 (学术词族)
3. ⭐⭐ Oxford 3000 (基础核心词)
4. ⭐⭐ COCA Academic (语料库验证)
5. ⭐ IELTS真题词汇 (针对性)
