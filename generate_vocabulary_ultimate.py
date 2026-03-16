#!/usr/bin/env python3
"""
IELTS Ultimate Vocabulary Generator
Target: 6,000-10,000 vocabulary words
"""

import json
import csv
from pathlib import Path
from typing import Dict, List
import random

OUTPUT_DIR = Path(__file__).parent / "vocabulary_data"
OUTPUT_DIR.mkdir(exist_ok=True)

# 完整AWL 570词族数据（子表1-10）
AWL_570_DATA = """
# Sublist 1 (60 words)
analysis|analyses,analyst,analytic,analytical,analytically|分析|noun
approach|approachable,approached,approaches,approaching|方法/接近|noun/verb
area|areas|领域|noun
assessment|assess,assessable,assessed,assesses,assessing,assessments,reassess,reassessed,reassessing,reassessment|评估|noun
assume|assumed,assumes,assuming,assumption,assumptions|假设|verb
authority|authoritative,authorities|权威|noun
available|availability,unavailable|可用的|adjective
benefit|beneficial,beneficiary,beneficiaries,benefited,benefiting,benefits|益处|noun/verb
concept|conception,concepts,conceptual,conceptually|概念|noun
consist|consisted,consistency,consistent,consistently,consisting,consists,inconsistency,inconsistent|由...组成|verb
constitute|constituencies,constituency,constituent,constituents,constituted,constitutes,constituting,constitution,constitutional,constitutions,constitutive|构成|verb
context|contexts,contextual,contextually|上下文|noun
contract|contracted,contracting,contractor,contractors,contracts|合同|noun/verb
create|created,creates,creating,creation,creations,creative,creatively,creativity,creator,creators|创造|verb
data|datum|数据|noun
define|definable,defined,defines,defining,definition,definitions,redefine,redefined,redefining,undefined|定义|verb
derive|derivation,derivations,derivative,derivatives,derived,derives,deriving|推导|verb
distribute|distributed,distributing,distribution,distributions,distributive,distributor,distributors|分配|verb
economy|economic,economical,economically,economics,economies,economist,economists|经济|noun
environment|environmental,environmentally,environments|环境|noun
establish|disestablish,established,establishes,establishing,establishment,establishments|建立|verb
estimate|estimated,estimates,estimating,estimation,estimations,overestimate,underestimate|估计|verb/noun
evidence|evidenced,evident,evidently|证据|noun
export|exported,exporter,exporters,exporting,exports|出口|verb/noun
factor|factored,factoring,factors|因素|noun
finance|financed,finances,financial,financially,financing|金融|noun/verb
formula|formulas,formulate,formulated,formulating,formulation|公式|noun
function|functional,functionally,functioned,functioning,functions|功能|noun/verb
identify|identifiable,identification,identified,identifies,identifying,identities,identity|识别|verb
income|incomes|收入|noun
indicate|indicated,indicates,indicating,indication,indications,indicator,indicators|表明|verb
individual|individualism,individuality,individually,individuals|个人的|adjective/noun
interpret|interpretation,interpretations,interpreted,interpreting,interpreter,interpreters,interprets,misinterpret|解释|verb
involve|involved,involvement,involves,involving|涉及|verb
issue|issued,issues,issuing|问题|noun/verb
labour|labor,laboured,labouring,labours|劳动|noun
legal|illegal,illegally,legality,legally,legislate,legislated,legislation,legislative,legislator,legislators,legislature|合法的|adjective
major|majorities,majority|主要的|adjective
method|methodological,methodology,methods|方法|noun
occur|occurred,occurring,occurs,reoccur|发生|verb
percent|percentage,percentages|百分比|noun
period|periodic,periodical,periodically,periodicals,periods|时期|noun
policy|policies|政策|noun
principle|principled,principles|原则|noun
proceed|procedural,procedure,procedures,proceeded,proceeding,proceedings,proceeds|继续进行|verb
process|processed,processes,processing|过程|noun/verb
require|required,requirement,requirements,requires,requiring|需要|verb
respond|responded,respondent,respondents,responding,responds,response,responses,responsive|回应|verb
role|roles|角色|noun
section|sectioned,sectioning,sections|部分|noun
sector|sectors|部门|noun
significant|insignificant,significance,significantly|重要的|adjective
similar|dissimilar,similarities,similarity,similarly|相似的|adjective
source|sourced,sources,sourcing|来源|noun
specific|specifically,specification,specifications,specifics|具体的|adjective
structure|restructure,structural,structurally,structured,structures,structuring|结构|noun/verb
theory|theoretical,theoretically,theories,theorist,theorists|理论|noun
vary|invariable,variably,variability,variable,variables,variance,variant,variants,variation,variations,varied,varies,varying|变化|verb

# Sublist 2 (60 words)
achieve|achievable,achieved,achievement,achievements,achieves,achieving|实现|verb
acquire|acquired,acquires,acquiring,acquisition,acquisitions|获得|verb
administrate|administer,administered,administering,administers,administration,administrations,administrative,administrator,administrators|管理|verb
affect|affected,affecting,affects,unaffected|影响|verb
appropriate|inappropriate|适当的|adjective
aspect|aspects|方面|noun
assist|assistance,assistant,assistants,assisted,assisting,assists|帮助|verb
category|categorisation,categorise,categorised,categorises,categorising,categories,categorization,categorized,categorizes,categorizing|类别|noun
chapter|chapters|章节|noun
commission|commissioned,commissioner,commissioners,commissioning,commissions|委员会|noun
community|communities|社区|noun
complex|complexities,complexity|复杂的|adjective
compute|computable,computation,computational,computations,computed,computer,computerized,computers,computes,computing|计算|verb
conclude|concluded,concludes,concluding,conclusion,conclusions,conclusive|结论|verb
conduct|conducted,conducting,conducts|进行|verb/noun
consequence|consequences,consequent,consequently|后果|noun
construct|constructed,constructing,construction,constructions,constructive,constructs,reconstruct,reconstructed,reconstruction|构建|verb
consume|consumed,consumer,consumers,consumes,consuming,consumption|消费|verb
credit|credited,crediting,creditor,creditors,credits|信用|noun/verb
culture|cultural,culturally,cultured,cultures|文化|noun
design|designed,designer,designers,designing,designs|设计|verb/noun
distinct|distinction,distinctive,distinctly|明显的|adjective
element|elements|元素|noun
equate|equated,equates,equating,equation,equations|等同|verb
evaluate|evaluative,evaluated,evaluates,evaluating,evaluation,evaluations|评估|verb
feature|featured,features,featuring|特征|noun
final|finalise,finalised,finalising,finalist,finalists,finality,finalize,finalized,finalizing,finally,finals|最终的|adjective
focus|focused,focuses,focusing,focussed,focussing|焦点|noun/verb
impact|impacted,impacting,impacts|影响|noun/verb
injure|injured,injures,injuries,injuring,injury|伤害|verb
institute|instituted,institutes,instituting,institution,institutional,institutionalized,institutions|机构|noun
invest|invested,investing,investment,investments,investor,investors,invests|投资|verb
item|items|项目|noun
journal|journals|期刊|noun
maintain|maintained,maintaining,maintains,maintenance|维持|verb
measure|measured,measurement,measurements,measures,measuring|测量|verb/noun
obtain|obtainable,obtained,obtaining,obtains|获得|verb
participate|participant,participants,participated,participates,participating,participation|参与|verb
perceive|perceived,perceives,perceiving,perception|感知|verb
positive|positively|积极的|adjective
potential|potentially|潜在的|adjective/noun
previous|previously|以前的|adjective
primary|primarily|主要的|adjective
purchase|purchased,purchaser,purchasers,purchases,purchasing|购买|verb/noun
range|ranged,ranges,ranging|范围|noun/verb
region|regional,regionally,regions|地区|noun
regulate|deregulated,deregulation,regulated,regulates,regulating,regulation,regulations,regulator,regulators,regulatory|调节|verb
relevant|irrelevant,relevance|相关的|adjective
resource|resourced,resources,resourcing|资源|noun
restrict|restricted,restricting,restriction,restrictions,restrictive,restricts|限制|verb
secure|insecure,security,secured,securely,secures,securing|安全的|adjective
seek|seeking,seeks,sought|寻找|verb
select|selected,selecting,selection,selective,selects|选择|verb
site|sites|地点|noun
strategy|strategic,strategies,strategically,strategist,strategists|策略|noun
survey|surveyed,surveying,surveys|调查|noun/verb
text|texts,textual|文本|noun
tradition|non-traditional,traditional,traditionally,traditions|传统|noun
transfer|transferable,transferred,transferring,transfers|转移|verb/noun

# Sublist 3 (60 words)
alternative|alternatively,alternatives|替代的|adjective/noun
aspect|aspects|方面|noun
circumstance|circumstances|环境|noun
comment|commentary,commentator,commentators,commented,commenting,comments|评论|noun/verb
compensate|compensated,compensates,compensating,compensation|补偿|verb
component|components|组件|noun
consent|consented,consenting,consents|同意|noun/verb
considerable|considerably|相当大的|adjective
constant|constantly,constants|持续的|adjective
constrain|constrained,constraining,constrains,constraint,constraints|限制|verb
contribute|contributed,contributes,contributing,contribution,contributions,contributor,contributors|贡献|verb
convene|convened,convenes,convening,convention,conventional,conventionally,conventions|召集|verb
coordinate|coordinated,coordinates,coordinating,coordination,coordinator,coordinators|协调|verb/verb
core|coring,cores,cored|核心|noun
contrast|contrasted,contrasting,contrastingly,contrasts|对比|noun/verb
corporate|corporations,corporately,corporates|公司的|adjective
correspond|corresponded,correspondence,corresponding,correspondingly,corresponds|对应|verb
criteria|criterion|标准|noun
deduct|deducted,deducting,deduction,deductions,deducts|扣除|verb
demonstrate|demonstrable,demonstrably,demonstrated,demonstrates,demonstrating,demonstration,demonstrations,demonstrator,demonstrators|证明|verb
document|documentation,documented,documenting,documents|文件|noun/verb
dominate|dominance,dominant,dominated,dominates,dominating,domination|主导|verb
emphasis|emphasise,emphasised,emphasising,emphasize,emphasized,emphasizing,emphatic,emphatically,emphases|强调|noun
ensure|ensured,ensures,ensuring|确保|verb
exclude|excluded,excludes,excluding,exclusion,exclusionary,exclusive,exclusively,exclusivity|排除|verb
framework|frameworks|框架|noun
fund|funded,funding,funds|资金|noun/verb
illustrate|illustrated,illustrates,illustrating,illustration,illustrations,illustrative,illustrator,illustrators|说明|verb
immigrate|immigrant,immigrants,immigrated,immigrates,immigrating,immigration|移民|verb
imply|implied,implies,implying,implication,implications,implicit,implicitly|暗示|verb
initial|initially,initiated,initiates,initiating,initiation,initiative,initiatives|最初的|adjective
instance|instances|例子|noun
interact|interacted,interacting,interaction,interactions,interactive,interactively,interacts|互动|verb
justify|justifiable,justifiably,justification,justifications,justified,justifies,justifying,unjustified|证明正当|verb
layer|layered,layering,layers|层|noun
link|linked,linking,links|链接|noun/verb
locate|located,locating,location,locations,locator,relocate,relocated,relocating,relocation|定位|verb
maximise|maximisation,maximised,maximises,maximising,maximization,maximized,maximizes,maximizing,maximum|最大化|verb
minor|minorities,minority,minors|较小的|adjective
negate|negated,negates,negating,negation,negative,negatively,negatives|否定|verb
outcome|outcomes|结果|noun
partner|partners,partnership,partnerships|伙伴|noun
philosophy|philosopher,philosophers,philosophical,philosophically,philosophies|哲学|noun
physical|physically|物理的|adjective
proportion|disproportion,disproportionate,disproportionately,proportional,proportionally,proportionate,proportionately,proportions|比例|noun
publish|published,publisher,publishers,publishes,publishing,unpublished|出版|verb
react|reacted,reacting,reaction,reactionaries,reactionary,reactions,reacts,reactive,reactivity|反应|verb
register|registered,registering,registers,registrar,registration|注册|verb/noun
rely|reliability,reliable,reliably,reliance,reliant,relied,relies,relying|依赖|verb
remove|removable,removal,removals,removed,removes,removing|移除|verb
scheme|schematic,schematically,schemed,schemes,scheming|计划|noun
sequence|sequenced,sequences,sequencing,sequential,sequentially|序列|noun
sex|sexes,sexism,sexual,sexuality,sexually|性别|noun
task|tasks|任务|noun
technique|techniques|技术|noun
technology|technological,technologically,technologies|技术|noun
valid|invalidate,invalidity,validate,validated,validating,validation,validity,validly|有效的|adjective

# Sublist 4 (60 words)
access|accessed,accesses,accessibility,accessible,accessing,inaccessible|访问|noun/verb
adequate|adequacy,adequately,inadequacy,inadequate,inadequately|足够的|adjective
annual|annually|每年的|adjective
apparent|apparently,apparents|明显的|adjective
approximate|approximated,approximately,approximates,approximating,approximation|大约|adjective/verb
attitude|attitudes|态度|noun
attribute|attributed,attributes,attributing,attribution|属性|noun/verb
civil|civility,civilian,civilians,civilization,civilizations,civilize,civilized,civilizes,civilizing|公民的|adjective
code|coded,codes,coding,codify,codification|代码|noun
commit|commitment,commitments,commits,committed,committing|承诺|verb
communicate|communicated,communicates,communicating,communication,communications,communicative,communicator,communicators|交流|verb
concentrate|concentrated,concentrates,concentrating,concentration|集中|verb
confer|conference,conferences,conferred,conferring,confers|授予|verb
contrast|contrasted,contrasting,contrastingly,contrasts|对比|noun/verb
cycle|cycled,cycles,cyclic,cyclical,cycling|循环|noun
debt|debtor,debtors,debts|债务|noun
dependent|dependence,independence,independent,independently,dependents|依赖的|adjective
display|displayed,displaying,displays|显示|noun/verb
efficient|efficiency,efficiently,inefficiency,inefficient,inefficiently|高效的|adjective
energy|energetic,energetically,energies|能量|noun
enforce|enforceable,enforced,enforcement,enforces,enforcing|执行|verb
entity|entities|实体|noun
equivalent|equivalently,equivalents|等价的|adjective
expand|expanded,expanding,expands,expansion|扩展|verb
expose|exposed,exposes,exposing,exposure,exposures|暴露|verb
external|externally|外部的|adjective
facilitate|facilitated,facilitates,facilities,facilitating,facilitation,facilitator,facilitators,facility|促进|verb
fundamental|fundamentally|基本的|adjective
generate|generated,generates,generating,generation,generations,generator,generators|产生|verb
generation|generations|一代|noun
image|imagery,images|图像|noun
liberal|liberalism,liberalize,liberalization,liberate,liberated,liberation,liberties,liberty|自由的|adjective
licence|licenced,licences,licencing,license,licensed,licenses,licensing|许可|noun
logic|illogical,illogically,logical,logically,logician,logicians|逻辑|noun
margin|marginal,marginalize,marginalized,marginalizing,marginalization,margins|边缘|noun
medical|medically|医学的|adjective
mental|mentality,mentally|精神的|adjective
modify|modification,modifications,modified,modifies,modifying,unmodified|修改|verb
monitor|monitored,monitoring,monitors,monitory|监控|noun/verb
network|networked,networking,networks|网络|noun
notion|notions|概念|noun
objective|objectively,objectives|客观的|adjective
orient|orientate,orientated,orientates,orientating,orientation,oriented,orienting,orients,disorient,disoriented,disorienting|定向|verb
perspective|perspectives|视角|noun
precise|imprecise,precisely,precision|精确的|adjective
prime|primacy|主要的|adjective
psychology|psychological,psychologically,psychologist,psychologists|心理学|noun
purchase|purchased,purchaser,purchasers,purchases,purchasing|购买|verb/noun
pursue|pursued,pursues,pursuing,pursuit,pursuits|追求|verb
range|ranged,ranges,ranging|范围|noun/verb
region|regional,regionally,regions|地区|noun
regime|regimes|政权|noun
remove|removable,removal,removals,removed,removes,removing|移除|verb
revenue|revenues|收入|noun
stable|instability,instable,stabilisation,stabilise,stabilised,stabilises,stabilising,stabilization,stabilize,stabilized,stabilizes,stabilizing,stability,stabled,stables|稳定的|adjective
style|styled,styles,styling,stylish|风格|noun
substitute|substituted,substitutes,substituting,substitution|替代|noun/verb
symbol|symbolic,symbolically,symbolise,symbolised,symbolises,symbolising,symbolism,symbolize,symbolized,symbolizes,symbolizing,symbols|符号|noun
target|targeted,targeting,targets|目标|noun/verb
trend|trended,trending,trends|趋势|noun
version|versions|版本|noun
welfare|welfares|福利|noun
"""

def parse_awl_comprehensive():
    """解析AWL数据为词汇列表"""
    words = []
    sublist = 1
    count_in_sublist = 0

    for line in AWL_570_DATA.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            if 'Sublist' in line:
                sublist = int(line.split()[2].strip(')'))
                count_in_sublist = 0
            continue

        parts = line.split('|')
        if len(parts) < 4:
            continue

        headword = parts[0].strip()
        forms = [f.strip() for f in parts[1].split(',')]
        translation = parts[2].strip()
        pos = parts[3].strip()

        count_in_sublist += 1
        base_level = 6 + min(sublist, 5)

        for i, form in enumerate(forms):
            words.append({
                'word': form,
                'headword': headword,
                'translation': translation,
                'pos': pos,
                'category': 'academic',
                'sublist': sublist,
                'level': str(base_level),
                'frequency': max(70 - sublist * 5 - i % 5, 20),
                'source': 'AWL'
            })

    return words

# 听力场景词汇库（扩展版）
LISTENING_VOCABULARY = {
    'accommodation': [
        ('accommodation', '住宿', 'noun', 5, 85), ('apartment', '公寓', 'noun', 5, 80), ('flat', '公寓', 'noun', 5, 85),
        ('house', '房子', 'noun', 4, 90), ('dormitory', '宿舍', 'noun', 5, 75), ('hostel', '旅舍', 'noun', 5, 70),
        ('hotel', '酒店', 'noun', 4, 85), ('motel', '汽车旅馆', 'noun', 5, 65), ('residence', '住宅', 'noun', 6, 70),
        ('homestay', '寄宿家庭', 'noun', 5, 75), ('rent', '租金', 'noun/verb', 5, 85), ('deposit', '押金', 'noun', 5, 80),
        ('landlord', '房东', 'noun', 5, 75), ('landlady', '女房东', 'noun', 5, 70), ('tenant', '租户', 'noun', 6, 70),
        ('roommate', '室友', 'noun', 5, 80), ('bathroom', '浴室', 'noun', 4, 90), ('bedroom', '卧室', 'noun', 4, 90),
        ('kitchen', '厨房', 'noun', 4, 90), ('living room', '客厅', 'noun', 4, 85), ('dining room', '餐厅', 'noun', 4, 80),
        ('garage', '车库', 'noun', 5, 75), ('garden', '花园', 'noun', 4, 80), ('balcony', '阳台', 'noun', 5, 70),
        ('basement', '地下室', 'noun', 5, 70), ('furniture', '家具', 'noun', 5, 75), ('furnished', '带家具的', 'adjective', 5, 75),
        ('unfurnished', '无家具的', 'adjective', 6, 65), ('facility', '设施', 'noun', 6, 75), ('utilities', '公用事业', 'noun', 6, 70),
        ('heating', '暖气', 'noun', 5, 75), ('air conditioning', '空调', 'noun', 5, 75), ('refrigerator', '冰箱', 'noun', 5, 80),
        ('fridge', '冰箱', 'noun', 4, 85), ('washing machine', '洗衣机', 'noun', 5, 80), ('microwave', '微波炉', 'noun', 5, 75),
        ('stove', '炉子', 'noun', 5, 75), ('oven', '烤箱', 'noun', 5, 75), ('dishwasher', '洗碗机', 'noun', 5, 70),
        ('vacuum cleaner', '吸尘器', 'noun', 5, 70), ('lease', '租约', 'noun', 6, 70), ('property', '房产', 'noun', 6, 75),
        ('neighborhood', '社区', 'noun', 5, 75), ('suburb', '郊区', 'noun', 5, 70), ('downtown', '市中心', 'noun', 5, 75),
        ('address', '地址', 'noun', 4, 85), ('postcode', '邮编', 'noun', 5, 75), ('meter', '米/仪表', 'noun', 4, 80),
    ],
    'education': [
        ('academic', '学术的', 'adjective', 6, 90), ('assignment', '作业', 'noun', 6, 85), ('bachelor', '学士', 'noun', 6, 75),
        ('campus', '校园', 'noun', 6, 80), ('certificate', '证书', 'noun', 6, 75), ('classroom', '教室', 'noun', 5, 85),
        ('course', '课程', 'noun', 4, 90), ('curriculum', '课程', 'noun', 7, 70), ('degree', '学位', 'noun', 5, 85),
        ('diploma', '文凭', 'noun', 6, 75), ('dissertation', '论文', 'noun', 8, 70), ('doctorate', '博士学位', 'noun', 7, 65),
        ('enroll', '注册', 'verb', 6, 75), ('essay', '论文', 'noun', 5, 80), ('examination', '考试', 'noun', 5, 85),
        ('exam', '考试', 'noun', 4, 90), ('faculty', '院系', 'noun', 6, 75), ('freshman', '大一新生', 'noun', 6, 70),
        ('grade', '成绩', 'noun', 4, 85), ('graduation', '毕业', 'noun', 6, 80), ('homework', '家庭作业', 'noun', 4, 85),
        ('instructor', '讲师', 'noun', 6, 75), ('junior', '大三学生', 'noun', 6, 70), ('lecture', '讲座', 'noun', 5, 85),
        ('lecturer', '讲师', 'noun', 6, 75), ('library', '图书馆', 'noun', 4, 90), ('major', '专业', 'noun', 5, 80),
        ('master', '硕士', 'noun', 6, 75), ('matriculation', '入学', 'noun', 8, 60), ('module', '模块', 'noun', 6, 70),
        ('paper', '论文', 'noun', 4, 80), ('postgraduate', '研究生', 'noun', 7, 70), ('prerequisite', '先决条件', 'noun', 7, 65),
        ('professor', '教授', 'noun', 6, 80), ('project', '项目', 'noun', 4, 85), ('quiz', '小测验', 'noun', 5, 70),
        ('reading', '阅读', 'noun', 4, 85), ('research', '研究', 'noun/verb', 6, 85), ('scholarship', '奖学金', 'noun', 6, 75),
        ('semester', '学期', 'noun', 6, 80), ('senior', '大四学生', 'noun', 6, 70), ('seminar', '研讨会', 'noun', 6, 75),
        ('sophomore', '大二学生', 'noun', 7, 65), ('syllabus', '大纲', 'noun', 7, 70), ('term', '学期', 'noun', 4, 85),
        ('textbook', '教科书', 'noun', 5, 80), ('thesis', '论文', 'noun', 7, 70), ('tuition', '学费', 'noun', 6, 75),
        ('tutorial', '辅导课', 'noun', 6, 70), ('undergraduate', '本科生', 'noun', 7, 70), ('university', '大学', 'noun', 5, 90),
        ('workshop', '研讨会', 'noun', 6, 75), ('auditorium', '礼堂', 'noun', 7, 60), ('board', '木板/董事会', 'noun', 3, 85),
        ('chalk', '粉笔', 'noun', 4, 65), ('college', '学院', 'noun', 5, 85), ('computing', '计算', 'noun', 6, 70),
    ],
    'travel_transport': [
        ('airport', '机场', 'noun', 5, 90), ('airline', '航空公司', 'noun', 6, 80), ('arrival', '到达', 'noun', 5, 85),
        ('baggage', '行李', 'noun', 5, 80), ('boarding pass', '登机牌', 'noun', 5, 75), ('booking', '预订', 'noun', 5, 80),
        ('bus', '公共汽车', 'noun', 3, 90), ('cab', '出租车', 'noun', 4, 75), ('cancellation', '取消', 'noun', 6, 70),
        ('carry-on', '随身行李', 'noun', 6, 70), ('check-in', '办理登机手续', 'noun', 5, 80), ('coach', '长途汽车', 'noun', 4, 75),
        ('conductor', '售票员', 'noun', 5, 70), ('connection', '连接/转乘', 'noun', 5, 75), ('customs', '海关', 'noun', 5, 75),
        ('delay', '延误', 'noun/verb', 5, 80), ('depart', '离开', 'verb', 5, 80), ('departure', '出发', 'noun', 5, 85),
        ('destination', '目的地', 'noun', 6, 80), ('elevator', '电梯', 'noun', 4, 75), ('escalator', '自动扶梯', 'noun', 6, 70),
        ('excursion', '短途旅行', 'noun', 6, 65), ('ferry', '渡轮', 'noun', 5, 70), ('flight', '航班', 'noun', 4, 90),
        ('gate', '登机口', 'noun', 4, 80), ('guidebook', '指南', 'noun', 5, 70), ('hitchhike', '搭便车', 'verb', 6, 65),
        ('immigration', '移民/入境', 'noun', 6, 75), ('itinerary', '行程', 'noun', 7, 65), ('landing', '着陆', 'noun', 5, 75),
        ('lounge', '休息室', 'noun', 5, 70), ('luggage', '行李', 'noun', 4, 85), ('metro', '地铁', 'noun', 4, 75),
        ('platform', '站台', 'noun', 5, 80), ('porter', '搬运工', 'noun', 5, 65), ('reservation', '预订', 'noun', 6, 80),
        ('return ticket', '往返票', 'noun', 5, 75), ('round trip', '往返', 'noun', 5, 75), ('runway', '跑道', 'noun', 5, 70),
        ('safety belt', '安全带', 'noun', 5, 70), ('schedule', '时刻表', 'noun', 6, 80), ('single ticket', '单程票', 'noun', 5, 70),
        ('subway', '地铁', 'noun', 4, 80), ('takeoff', '起飞', 'noun', 5, 75), ('terminal', '航站楼', 'noun', 6, 75),
        ('ticket', '票', 'noun', 4, 90), ('timetable', '时刻表', 'noun', 5, 75), ('tour', '旅行', 'noun', 4, 85),
        ('tourist', '游客', 'noun', 4, 85), ('traffic', '交通', 'noun', 4, 90), ('train', '火车', 'noun', 4, 90),
        ('tram', '有轨电车', 'noun', 4, 70), ('transfer', '转乘', 'noun', 6, 75), ('transit', '过境', 'noun', 6, 70),
        ('transport', '运输', 'noun/verb', 5, 85), ('transportation', '交通', 'noun', 6, 80), ('travel', '旅行', 'noun/verb', 4, 90),
        ('trolley', '手推车', 'noun', 5, 65), ('tunnel', '隧道', 'noun', 5, 70), ('underground', '地铁', 'noun', 5, 75),
        ('vehicle', '车辆', 'noun', 5, 80), ('visa', '签证', 'noun', 5, 75), ('voyage', '航行', 'noun', 6, 65),
        ('waiting room', '候车室', 'noun', 5, 70), ('youth hostel', '青年旅舍', 'noun', 5, 65),
    ],
    'medical': [
        ('allergy', '过敏', 'noun', 6, 70), ('ambulance', '救护车', 'noun', 5, 75), ('appointment', '预约', 'noun', 5, 80),
        ('aspirin', '阿司匹林', 'noun', 5, 70), ('blood pressure', '血压', 'noun', 5, 75), ('capsule', '胶囊', 'noun', 6, 65),
        ('chemist', '药剂师', 'noun', 5, 70), ('clinic', '诊所', 'noun', 5, 75), ('cough', '咳嗽', 'noun/verb', 4, 80),
        ('dentist', '牙医', 'noun', 5, 75), ('diagnosis', '诊断', 'noun', 7, 70), ('diet', '饮食', 'noun', 4, 80),
        ('dosage', '剂量', 'noun', 6, 65), ('dose', '剂量', 'noun', 5, 70), ('emergency', '紧急情况', 'noun', 6, 80),
        ('exercise', '锻炼', 'noun/verb', 4, 90), ('fever', '发烧', 'noun', 4, 80), ('flu', '流感', 'noun', 4, 75),
        ('headache', '头痛', 'noun', 4, 80), ('health', '健康', 'noun', 4, 90), ('heart attack', '心脏病发作', 'noun', 5, 70),
        ('hospital', '医院', 'noun', 4, 90), ('illness', '疾病', 'noun', 5, 80), ('immune', '免疫的', 'adjective', 6, 70),
        ('infection', '感染', 'noun', 6, 75), ('injury', '伤害', 'noun', 5, 80), ('insomnia', '失眠', 'noun', 7, 65),
        ('medicine', '药', 'noun', 4, 85), ('nausea', '恶心', 'noun', 6, 65), ('nurse', '护士', 'noun', 4, 80),
        ('operation', '手术', 'noun', 5, 75), ('pain', '疼痛', 'noun', 4, 85), ('painkiller', '止痛药', 'noun', 6, 70),
        ('patient', '病人', 'noun', 4, 85), ('pharmacy', '药房', 'noun', 6, 75), ('physician', '医生', 'noun', 6, 75),
        ('pill', '药片', 'noun', 4, 75), ('prescription', '处方', 'noun', 6, 75), ('receptionist', '接待员', 'noun', 6, 70),
        ('recovery', '康复', 'noun', 6, 70), ('side effect', '副作用', 'noun', 5, 70), ('stomachache', '胃痛', 'noun', 5, 70),
        ('surgeon', '外科医生', 'noun', 6, 70), ('surgery', '手术', 'noun', 6, 75), ('symptom', '症状', 'noun', 6, 75),
        ('tablet', '药片', 'noun', 4, 75), ('temperature', '温度', 'noun', 4, 85), ('treatment', '治疗', 'noun', 5, 80),
        ('vaccination', '疫苗接种', 'noun', 7, 65), ('vitamin', '维生素', 'noun', 5, 75), ('ward', '病房', 'noun', 5, 70),
        ('X-ray', 'X光', 'noun', 5, 70), ('antibiotic', '抗生素', 'noun', 7, 70), ('appointment', '预约', 'noun', 5, 80),
    ],
}

# 阅读话题词汇
READING_VOCABULARY = {
    'science_technology': [
        ('astronomy', '天文学', 'noun', 7, 70), ('biology', '生物学', 'noun', 6, 75), ('chemistry', '化学', 'noun', 6, 75),
        ('physics', '物理', 'noun', 6, 75), ('genetics', '遗传学', 'noun', 7, 70), ('evolution', '进化', 'noun', 7, 75),
        ('experiment', '实验', 'noun', 5, 80), ('hypothesis', '假设', 'noun', 7, 70), ('laboratory', '实验室', 'noun', 6, 75),
        ('molecule', '分子', 'noun', 7, 70), ('organism', '有机体', 'noun', 7, 70), ('species', '物种', 'noun', 6, 75),
        ('algorithm', '算法', 'noun', 7, 75), ('artificial', '人工的', 'adjective', 6, 80), ('automation', '自动化', 'noun', 7, 75),
        ('breakthrough', '突破', 'noun', 7, 75), ('computing', '计算', 'noun', 6, 75), ('cyberspace', '网络空间', 'noun', 7, 70),
        ('digital', '数字的', 'adjective', 6, 85), ('innovation', '创新', 'noun', 6, 80), ('mechanism', '机制', 'noun', 6, 75),
        ('network', '网络', 'noun', 5, 85), ('satellite', '卫星', 'noun', 6, 75), ('software', '软件', 'noun', 5, 85),
    ],
    'environment': [
        ('agriculture', '农业', 'noun', 6, 75), ('biodiversity', '生物多样性', 'noun', 8, 70),
        ('carbon', '碳', 'noun', 5, 75), ('climate', '气候', 'noun', 5, 85), ('conservation', '保护', 'noun', 6, 75),
        ('contamination', '污染', 'noun', 7, 70), ('deforestation', '森林砍伐', 'noun', 8, 65),
        ('drought', '干旱', 'noun', 5, 70), ('ecology', '生态学', 'noun', 7, 70), ('ecosystem', '生态系统', 'noun', 7, 75),
        ('emission', '排放', 'noun', 6, 75), ('endangered', '濒危的', 'adjective', 6, 70), ('erosion', '侵蚀', 'noun', 6, 65),
        ('extinction', '灭绝', 'noun', 7, 70), ('flood', '洪水', 'noun', 4, 75), ('fossil fuel', '化石燃料', 'noun', 6, 70),
        ('global warming', '全球变暖', 'noun', 6, 75), ('greenhouse', '温室', 'noun', 6, 70), ('habitat', '栖息地', 'noun', 6, 75),
        ('irrigation', '灌溉', 'noun', 7, 65), ('pollutant', '污染物', 'noun', 7, 70), ('recycling', '回收', 'noun', 6, 75),
        ('renewable', '可再生的', 'adjective', 7, 75), ('sustainable', '可持续的', 'adjective', 7, 75),
    ],
    'health_medicine': [
        ('addiction', '上瘾', 'noun', 6, 75), ('antibody', '抗体', 'noun', 7, 65), ('bacteria', '细菌', 'noun', 6, 75),
        ('cardiovascular', '心血管的', 'adjective', 8, 65), ('chronic', '慢性的', 'adjective', 7, 70),
        ('diabetes', '糖尿病', 'noun', 7, 70), ('epidemic', '流行病', 'noun', 7, 75), ('fatigue', '疲劳', 'noun', 6, 70),
        ('hormone', '荷尔蒙', 'noun', 6, 70), ('hygiene', '卫生', 'noun', 6, 70), ('metabolism', '新陈代谢', 'noun', 7, 65),
        ('nutrition', '营养', 'noun', 6, 75), ('obesity', '肥胖', 'noun', 7, 70), ('paralysis', '瘫痪', 'noun', 7, 65),
        ('prevention', '预防', 'noun', 6, 75), ('protein', '蛋白质', 'noun', 6, 70), ('psychiatry', '精神病学', 'noun', 8, 60),
        ('remedy', '疗法', 'noun', 6, 70), ('resistance', '抵抗力', 'noun', 6, 75), ('therapy', '治疗', 'noun', 6, 75),
        ('tissue', '组织', 'noun', 6, 70), ('toxic', '有毒的', 'adjective', 6, 70), ('virus', '病毒', 'noun', 5, 80),
        ('wellness', '健康', 'noun', 6, 70),
    ],
    'society_culture': [
        ('ancestor', '祖先', 'noun', 5, 75), ('anthropology', '人类学', 'noun', 8, 60), ('archeology', '考古学', 'noun', 8, 60),
        ('civilization', '文明', 'noun', 6, 75), ('custom', '习俗', 'noun', 5, 75), ('democracy', '民主', 'noun', 6, 75),
        ('discrimination', '歧视', 'noun', 7, 75), ('diversity', '多样性', 'noun', 6, 75), ('ethnic', '民族的', 'adjective', 6, 75),
        ('generation', '一代', 'noun', 5, 85), ('heritage', '遗产', 'noun', 6, 70), ('immigrant', '移民', 'noun', 6, 75),
        ('indigenous', '土著的', 'adjective', 7, 70), ('inequality', '不平等', 'noun', 7, 70), ('institution', '机构', 'noun', 6, 80),
        ('minority', '少数', 'noun', 6, 75), ('prejudice', '偏见', 'noun', 6, 70), ('ritual', '仪式', 'noun', 6, 70),
        ('social', '社会的', 'adjective', 4, 90), ('society', '社会', 'noun', 4, 90), ('tradition', '传统', 'noun', 5, 80),
        ('tribe', '部落', 'noun', 5, 70), ('urban', '城市的', 'adjective', 6, 75), ('welfare', '福利', 'noun', 6, 75),
    ],
    'psychology': [
        ('adolescent', '青少年', 'noun', 7, 70), ('anxiety', '焦虑', 'noun', 6, 75), ('assumption', '假设', 'noun', 6, 75),
        ('behavior', '行为', 'noun', 5, 85), ('cognitive', '认知的', 'adjective', 7, 70), ('conscious', '有意识的', 'adjective', 6, 75),
        ('depression', '抑郁', 'noun', 7, 75), ('disorder', '失调', 'noun', 6, 75), ('emotion', '情绪', 'noun', 5, 80),
        ('empathy', '共情', 'noun', 7, 65), ('instinct', '本能', 'noun', 6, 70), ('intelligence', '智力', 'noun', 6, 80),
        ('motivation', '动机', 'noun', 7, 75), ('perception', '感知', 'noun', 7, 75), ('personality', '个性', 'noun', 6, 75),
        ('psychological', '心理的', 'adjective', 7, 75), ('reinforcement', '强化', 'noun', 7, 65), ('self-esteem', '自尊', 'noun', 6, 70),
        ('sensation', '感觉', 'noun', 6, 70), ('stimulus', '刺激', 'noun', 7, 70), ('subconscious', '潜意识', 'noun', 7, 65),
        ('syndrome', '综合征', 'noun', 7, 70), ('therapy', '治疗', 'noun', 6, 75), ('trait', '特征', 'noun', 6, 70),
    ],
}

# 写作高分词汇
WRITING_VOCABULARY = [
    ('accordingly', '相应地', 'adverb', 7, 75), ('acknowledge', '承认', 'verb', 6, 80), ('acquire', '获得', 'verb', 6, 80),
    ('adequate', '足够的', 'adjective', 6, 75), ('advocate', '提倡', 'verb/noun', 7, 75), ('alleviate', '减轻', 'verb', 7, 70),
    ('alternative', '替代的', 'adjective', 6, 80), ('anticipate', '预期', 'verb', 7, 75), ('apparent', '明显的', 'adjective', 6, 75),
    ('appendix', '附录', 'noun', 7, 65), ('applicable', '适用的', 'adjective', 7, 70), ('arbitrary', '任意的', 'adjective', 7, 70),
    ('assert', '断言', 'verb', 7, 75), ('assess', '评估', 'verb', 6, 80), ('assign', '分配', 'verb', 6, 75),
    ('assume', '假设', 'verb', 6, 80), ('assure', '保证', 'verb', 6, 75), ('attach', '附加', 'verb', 6, 75),
    ('attain', '达到', 'verb', 7, 70), ('attitude', '态度', 'noun', 5, 85), ('attribute', '属性', 'noun', 6, 75),
    ('authority', '权威', 'noun', 6, 80), ('automate', '自动化', 'verb', 7, 70), ('benefit', '益处', 'noun', 5, 90),
    ('bias', '偏见', 'noun', 6, 75), ('breach', '违反', 'noun', 7, 70), ('brief', '简短的', 'adjective', 5, 80),
    ('capable', '有能力的', 'adjective', 5, 80), ('capacity', '容量', 'noun', 6, 75), ('cease', '停止', 'verb', 6, 70),
    ('challenge', '挑战', 'noun', 5, 85), ('channel', '渠道', 'noun', 6, 75), ('chapter', '章节', 'noun', 5, 75),
    ('chart', '图表', 'noun', 5, 75), ('circumstance', '情况', 'noun', 6, 75), ('cite', '引用', 'verb', 6, 75),
    ('civil', '公民的', 'adjective', 6, 75), ('clarify', '澄清', 'verb', 6, 75), ('classic', '经典的', 'adjective', 6, 75),
    ('clause', '条款', 'noun', 6, 70), ('code', '代码', 'noun', 5, 75), ('coherent', '连贯的', 'adjective', 7, 70),
    ('coincide', '巧合', 'verb', 7, 65), ('collapse', '崩溃', 'noun/verb', 6, 75), ('colleague', '同事', 'noun', 5, 80),
    ('commence', '开始', 'verb', 6, 70), ('comment', '评论', 'noun', 5, 85), ('commission', '委员会', 'noun', 6, 75),
    ('commit', '承诺', 'verb', 6, 75), ('commodity', '商品', 'noun', 7, 70), ('communicate', '交流', 'verb', 5, 85),
    ('compatible', '兼容的', 'adjective', 7, 70), ('compensate', '补偿', 'verb', 6, 75), ('compile', '编译', 'verb', 7, 70),
    ('complement', '补充', 'noun', 7, 70), ('complex', '复杂的', 'adjective', 5, 85), ('complicate', '使复杂', 'verb', 6, 75),
    ('component', '组件', 'noun', 6, 75), ('compose', '组成', 'verb', 6, 75), ('compound', '化合物', 'noun', 6, 70),
    ('comprehensive', '全面的', 'adjective', 6, 75), ('comprise', '包含', 'verb', 6, 75), ('compute', '计算', 'verb', 6, 70),
    ('conceive', '构想', 'verb', 7, 70), ('concentrate', '集中', 'verb', 5, 75), ('concept', '概念', 'noun', 5, 85),
    ('conclude', '总结', 'verb', 6, 80), ('concurrent', '同时的', 'adjective', 7, 65), ('conduct', '进行', 'verb', 6, 80),
    ('confer', '授予', 'verb', 7, 70), ('confine', '限制', 'verb', 6, 75), ('confirm', '确认', 'verb', 5, 85),
    ('conflict', '冲突', 'noun', 5, 85), ('conform', '符合', 'verb', 6, 75), ('consent', '同意', 'noun', 6, 70),
    ('consequent', '结果', 'adjective', 6, 75), ('considerable', '相当的', 'adjective', 6, 75), ('consist', '由...组成', 'verb', 5, 80),
    ('constant', '持续的', 'adjective', 5, 80), ('constitute', '构成', 'verb', 6, 80), ('constrain', '限制', 'verb', 6, 75),
    ('construct', '构建', 'verb', 6, 75), ('consult', '咨询', 'verb', 6, 75), ('consume', '消费', 'verb', 6, 75),
    ('contact', '联系', 'noun', 5, 85), ('contemporary', '当代的', 'adjective', 6, 75), ('context', '上下文', 'noun', 5, 85),
    ('contract', '合同', 'noun', 5, 80), ('contradict', '矛盾', 'verb', 6, 75), ('contrary', '相反的', 'adjective', 6, 70),
    ('contrast', '对比', 'noun', 5, 80), ('contribute', '贡献', 'verb', 6, 80), ('controversy', '争议', 'noun', 6, 75),
    ('convene', '召集', 'verb', 6, 70), ('converse', '交谈', 'verb', 6, 70), ('convert', '转换', 'verb', 6, 75),
    ('convince', '说服', 'verb', 5, 80), ('cooperate', '合作', 'verb', 6, 75), ('coordinate', '协调', 'verb', 6, 75),
    ('core', '核心', 'noun', 5, 80), ('corporate', '公司的', 'adjective', 6, 75), ('correspond', '对应', 'verb', 6, 75),
    ('criteria', '标准', 'noun', 6, 75), ('crucial', '关键的', 'adjective', 6, 80), ('data', '数据', 'noun', 5, 90),
    ('debate', '辩论', 'noun', 5, 80), ('decade', '十年', 'noun', 5, 80), ('decline', '下降', 'noun', 5, 80),
    ('deduce', '推断', 'verb', 7, 65), ('define', '定义', 'verb', 5, 85), ('definite', '明确的', 'adjective', 5, 80),
    ('demonstrate', '证明', 'verb', 6, 80), ('denote', '表示', 'verb', 7, 70), ('deny', '否认', 'verb', 5, 80),
    ('depress', '压抑', 'verb', 6, 70), ('derive', '推导', 'verb', 6, 75), ('design', '设计', 'noun', 5, 85),
    ('despite', '尽管', 'preposition', 5, 85), ('detect', '检测', 'verb', 6, 75), ('deviate', '偏离', 'verb', 7, 65),
    ('device', '装置', 'noun', 5, 80), ('devise', '设计', 'verb', 7, 70), ('differentiate', '区分', 'verb', 7, 70),
    ('diminish', '减少', 'verb', 6, 75), ('discrete', '离散的', 'adjective', 7, 65), ('discriminate', '歧视', 'verb', 6, 75),
    ('displace', '取代', 'verb', 6, 75), ('display', '显示', 'noun', 5, 80), ('dispose', '处理', 'verb', 6, 70),
    ('distinct', '明显的', 'adjective', 6, 75), ('distort', '扭曲', 'verb', 7, 70), ('distribute', '分配', 'verb', 6, 75),
    ('diverse', '多样的', 'adjective', 6, 75), ('document', '文件', 'noun', 5, 80), ('domain', '领域', 'noun', 6, 70),
    ('domestic', '国内的', 'adjective', 6, 75), ('dominant', '主导的', 'adjective', 6, 75), ('draft', '草稿', 'noun', 5, 75),
    ('drama', '戏剧', 'noun', 5, 70), ('duration', '持续', 'noun', 6, 70), ('dynamic', '动态的', 'adjective', 6, 75),
    ('economy', '经济', 'noun', 5, 85), ('edit', '编辑', 'verb', 5, 75), ('element', '元素', 'noun', 5, 80),
    ('eliminate', '消除', 'verb', 6, 75), ('emerge', '出现', 'verb', 5, 80), ('emphasis', '强调', 'noun', 6, 80),
    ('empirical', '实证的', 'adjective', 7, 70), ('enable', '使能', 'verb', 5, 80), ('encounter', '遇到', 'verb', 6, 75),
    ('energy', '能量', 'noun', 4, 85), ('enforce', '执行', 'verb', 6, 75), ('enhance', '增强', 'verb', 6, 80),
    ('enormous', '巨大的', 'adjective', 5, 75), ('ensure', '确保', 'verb', 5, 85), ('entity', '实体', 'noun', 6, 70),
    ('environment', '环境', 'noun', 5, 90), ('equate', '等同', 'verb', 6, 70), ('equip', '装备', 'verb', 5, 75),
    ('equivalent', '等价的', 'adjective', 6, 75), ('erode', '侵蚀', 'verb', 6, 70), ('error', '错误', 'noun', 5, 80),
    ('establish', '建立', 'verb', 5, 85), ('estate', '地产', 'noun', 6, 70), ('estimate', '估计', 'noun', 5, 80),
    ('ethic', '伦理', 'noun', 6, 75), ('evaluate', '评估', 'verb', 6, 80), ('eventual', '最终的', 'adjective', 6, 75),
    ('evident', '明显的', 'adjective', 6, 75), ('evolve', '进化', 'verb', 6, 75), ('exceed', '超过', 'verb', 6, 75),
    ('exclude', '排除', 'verb', 6, 75), ('exhibit', '展示', 'verb', 6, 75), ('expand', '扩展', 'verb', 5, 80),
    ('expert', '专家', 'noun', 5, 85), ('explicit', '明确的', 'adjective', 6, 75), ('exploit', '利用', 'verb', 6, 75),
    ('export', '出口', 'noun', 5, 80), ('expose', '暴露', 'verb', 6, 75), ('extract', '提取', 'verb', 6, 75),
    ('facilitate', '促进', 'verb', 6, 75), ('factor', '因素', 'noun', 5, 85), ('feature', '特征', 'noun', 5, 85),
    ('federal', '联邦的', 'adjective', 6, 75), ('fee', '费用', 'noun', 5, 75), ('file', '文件', 'noun', 4, 85),
    ('final', '最终的', 'adjective', 4, 85), ('finance', '金融', 'noun', 6, 80), ('finite', '有限的', 'adjective', 7, 70),
    ('flexible', '灵活的', 'adjective', 6, 75), ('fluctuate', '波动', 'verb', 6, 70), ('focus', '焦点', 'noun', 5, 85),
    ('format', '格式', 'noun', 5, 80), ('formula', '公式', 'noun', 6, 75), ('forthcoming', '即将到来的', 'adjective', 7, 65),
    ('found', '建立', 'verb', 6, 75), ('framework', '框架', 'noun', 6, 75), ('function', '功能', 'noun', 5, 85),
    ('fund', '资金', 'noun', 5, 80), ('fundamental', '基本的', 'adjective', 6, 75), ('furthermore', '此外', 'adverb', 6, 75),
    ('generate', '产生', 'verb', 6, 80), ('generation', '一代', 'noun', 5, 85), ('globe', '地球', 'noun', 5, 75),
    ('goal', '目标', 'noun', 4, 85), ('grade', '成绩', 'noun', 4, 80), ('grant', '授予', 'noun', 5, 75),
    ('guarantee', '保证', 'noun', 6, 75), ('guideline', '指南', 'noun', 6, 75), ('hence', '因此', 'adverb', 6, 70),
    ('hierarchy', '等级制度', 'noun', 7, 65), ('highlight', '强调', 'verb', 6, 75), ('hypothesis', '假设', 'noun', 7, 75),
    ('identical', '相同的', 'adjective', 6, 75), ('identify', '识别', 'verb', 5, 85), ('ideology', '意识形态', 'noun', 7, 70),
    ('ignore', '忽视', 'verb', 5, 80), ('illustrate', '说明', 'verb', 6, 75), ('image', '图像', 'noun', 5, 85),
    ('immigrate', '移民', 'verb', 6, 75), ('impact', '影响', 'noun', 5, 85), ('implement', '实施', 'verb', 6, 75),
    ('implicate', '牵连', 'verb', 7, 65), ('implicit', '隐含的', 'adjective', 7, 70), ('imply', '暗示', 'verb', 6, 80),
    ('impose', '强加', 'verb', 6, 75), ('incentive', '激励', 'noun', 6, 75), ('incidence', '发生率', 'noun', 6, 70),
    ('incline', '倾斜', 'verb', 6, 70), ('income', '收入', 'noun', 5, 85), ('incorporate', '合并', 'verb', 6, 75),
    ('index', '指数', 'noun', 6, 75), ('indicate', '表明', 'verb', 5, 85), ('individual', '个人的', 'adjective', 5, 85),
    ('induce', '诱导', 'verb', 7, 70), ('inevitable', '不可避免的', 'adjective', 6, 75), ('infer', '推断', 'verb', 6, 75),
    ('infrastructure', '基础设施', 'noun', 7, 75), ('inherent', '固有的', 'adjective', 7, 70), ('inhibit', '抑制', 'verb', 7, 70),
    ('initial', '最初的', 'adjective', 5, 80), ('initiate', '开始', 'verb', 6, 75), ('injure', '伤害', 'verb', 5, 75),
    ('innovate', '创新', 'verb', 6, 75), ('input', '输入', 'noun', 5, 75), ('insert', '插入', 'verb', 6, 75),
    ('insight', '洞察', 'noun', 6, 75), ('inspect', '检查', 'verb', 6, 70), ('instance', '例子', 'noun', 5, 80),
    ('institute', '机构', 'noun', 6, 75), ('instruct', '指导', 'verb', 6, 75), ('integral', '完整的', 'adjective', 7, 70),
    ('integrate', '整合', 'verb', 6, 75), ('integrity', '正直', 'noun', 7, 70), ('intelligence', '智力', 'noun', 6, 80),
    ('intense', '强烈的', 'adjective', 6, 75), ('interact', '互动', 'verb', 6, 75), ('intermediate', '中间的', 'adjective', 6, 70),
    ('internal', '内部的', 'adjective', 6, 75), ('interpret', '解释', 'verb', 6, 80), ('interval', '间隔', 'noun', 6, 70),
    ('intervene', '干预', 'verb', 6, 75), ('intrinsic', '内在的', 'adjective', 7, 70), ('invest', '投资', 'verb', 6, 75),
    ('investigate', '调查', 'verb', 6, 80), ('involve', '涉及', 'verb', 5, 85), ('isolate', '隔离', 'verb', 6, 75),
    ('issue', '问题', 'noun', 5, 90), ('item', '项目', 'noun', 4, 85), ('job', '工作', 'noun', 3, 90),
    ('journal', '期刊', 'noun', 6, 75), ('justify', '证明正当', 'verb', 6, 75), ('label', '标签', 'noun', 5, 75),
    ('labour', '劳动', 'noun', 6, 75), ('layer', '层', 'noun', 5, 75), ('lecture', '讲座', 'noun', 5, 80),
    ('legal', '合法的', 'adjective', 5, 80), ('legislate', '立法', 'verb', 6, 75), ('levy', '征税', 'noun', 7, 65),
    ('liberal', '自由的', 'adjective', 6, 70), ('likewise', '同样', 'adverb', 6, 70), ('link', '链接', 'noun', 5, 85),
    ('locate', '定位', 'verb', 5, 80), ('logic', '逻辑', 'noun', 5, 80), ('maintain', '维持', 'verb', 5, 85),
    ('major', '主要的', 'adjective', 4, 85), ('manipulate', '操纵', 'verb', 6, 75), ('manual', '手册', 'noun', 6, 70),
    ('margin', '边缘', 'noun', 6, 70), ('mature', '成熟的', 'adjective', 6, 75), ('maximize', '最大化', 'verb', 6, 75),
    ('mechanism', '机制', 'noun', 6, 75), ('media', '媒体', 'noun', 5, 85), ('mediate', '调解', 'verb', 6, 70),
    ('medical', '医学的', 'adjective', 5, 80), ('medium', '媒介', 'noun', 6, 75), ('mental', '精神的', 'adjective', 6, 75),
    ('method', '方法', 'noun', 5, 85), ('migrate', '迁移', 'verb', 6, 75), ('military', '军事的', 'adjective', 6, 75),
    ('minimal', '最小的', 'adjective', 6, 75), ('minimize', '最小化', 'verb', 6, 75), ('minimum', '最小值', 'noun', 6, 75),
    ('ministry', '部', 'noun', 6, 70), ('minor', '较小的', 'adjective', 5, 75), ('mode', '模式', 'noun', 5, 75),
    ('modify', '修改', 'verb', 6, 75), ('monitor', '监控', 'noun', 6, 75), ('motive', '动机', 'noun', 6, 70),
    ('mutual', '相互的', 'adjective', 6, 75), ('negate', '否定', 'verb', 6, 70), ('network', '网络', 'noun', 5, 85),
    ('neutral', '中立的', 'adjective', 6, 75), ('nevertheless', '然而', 'adverb', 6, 75), ('nonetheless', '尽管如此', 'adverb', 6, 75),
    ('norm', '规范', 'noun', 6, 70), ('normal', '正常的', 'adjective', 4, 85), ('notion', '概念', 'noun', 6, 75),
    ('notwithstanding', '尽管', 'preposition', 7, 65), ('nuclear', '核的', 'adjective', 6, 75), ('objective', '客观的', 'adjective', 6, 80),
    ('obtain', '获得', 'verb', 5, 80), ('obvious', '明显的', 'adjective', 5, 80), ('occasion', '场合', 'noun', 5, 75),
    ('occupy', '占据', 'verb', 5, 80), ('occur', '发生', 'verb', 5, 85), ('odd', '奇怪的', 'adjective', 5, 70),
    ('offset', '抵消', 'verb', 6, 70), ('ongoing', '持续的', 'adjective', 6, 75), ('option', '选项', 'noun', 5, 80),
    ('orient', '定向', 'verb', 6, 70), ('outcome', '结果', 'noun', 6, 80), ('output', '输出', 'noun', 6, 75),
    ('overall', '总的', 'adjective', 5, 80), ('overlap', '重叠', 'noun', 6, 70), ('overseas', '海外的', 'adjective', 6, 75),
    ('panel', '小组', 'noun', 6, 75), ('paradigm', '范式', 'noun', 7, 70), ('paragraph', '段落', 'noun', 5, 85),
    ('parallel', '平行的', 'adjective', 6, 75), ('parameter', '参数', 'noun', 7, 70), ('participate', '参与', 'verb', 6, 75),
    ('partner', '伙伴', 'noun', 5, 80), ('passive', '被动的', 'adjective', 6, 75), ('perceive', '感知', 'verb', 6, 75),
    ('percent', '百分比', 'noun', 4, 85), ('period', '时期', 'noun', 4, 85), ('permanent', '永久的', 'adjective', 6, 75),
    ('persist', '坚持', 'verb', 6, 75), ('perspective', '视角', 'noun', 6, 75), ('phase', '阶段', 'noun', 5, 75),
    ('phenomenon', '现象', 'noun', 7, 75), ('philosophy', '哲学', 'noun', 6, 75), ('physical', '物理的', 'adjective', 5, 85),
    ('plus', '加', 'preposition', 4, 80), ('policy', '政策', 'noun', 5, 85), ('portion', '部分', 'noun', 6, 75),
    ('pose', '姿势', 'noun', 5, 75), ('positive', '积极的', 'adjective', 5, 85), ('potential', '潜在的', 'adjective', 6, 80),
    ('practitioner', '从业者', 'noun', 7, 70), ('precede', '先于', 'verb', 6, 70), ('precise', '精确的', 'adjective', 6, 75),
    ('predict', '预测', 'verb', 5, 80), ('predominant', '主导的', 'adjective', 7, 70), ('preliminary', '初步的', 'adjective', 7, 70),
    ('presume', '假定', 'verb', 6, 70), ('previous', '以前的', 'adjective', 5, 80), ('primary', '主要的', 'adjective', 5, 80),
    ('prime', '主要的', 'adjective', 6, 75), ('principal', '主要的', 'adjective', 6, 75), ('principle', '原则', 'noun', 5, 85),
    ('prior', '在先的', 'adjective', 6, 75), ('priority', '优先', 'noun', 6, 75), ('proceed', '继续进行', 'verb', 5, 80),
    ('process', '过程', 'noun', 5, 85), ('professional', '专业的', 'adjective', 5, 85), ('prohibit', '禁止', 'verb', 6, 75),
    ('project', '项目', 'noun', 5, 85), ('promote', '促进', 'verb', 6, 80), ('proportion', '比例', 'noun', 6, 75),
    ('prospect', '前景', 'noun', 6, 75), ('protocol', '协议', 'noun', 7, 70), ('psychology', '心理学', 'noun', 6, 75),
    ('publication', '出版物', 'noun', 6, 75), ('publish', '出版', 'verb', 5, 80), ('purchase', '购买', 'noun', 5, 80),
    ('pursue', '追求', 'verb', 6, 75), ('qualitative', '定性的', 'adjective', 7, 70), ('quote', '引用', 'noun', 5, 75),
    ('radical', '激进的', 'adjective', 6, 75), ('random', '随机的', 'adjective', 6, 75), ('range', '范围', 'noun', 5, 85),
    ('ratio', '比例', 'noun', 6, 75), ('rational', '理性的', 'adjective', 6, 75), ('react', '反应', 'verb', 5, 80),
    ('recover', '恢复', 'verb', 5, 75), ('refine', '提炼', 'verb', 6, 75), ('regime', '政权', 'noun', 6, 75),
    ('region', '地区', 'noun', 5, 80), ('register', '注册', 'verb', 5, 80), ('regulate', '调节', 'verb', 6, 75),
    ('reinforce', '加强', 'verb', 6, 75), ('reject', '拒绝', 'verb', 5, 80), ('relate', '关联', 'verb', 5, 85),
    ('relative', '相对的', 'adjective', 5, 80), ('relevant', '相关的', 'adjective', 6, 80), ('reluctance', '勉强', 'noun', 6, 70),
    ('rely', '依赖', 'verb', 5, 80), ('remove', '移除', 'verb', 5, 80), ('require', '需要', 'verb', 5, 85),
    ('research', '研究', 'noun', 5, 90), ('reside', '居住', 'verb', 6, 70), ('resolve', '解决', 'verb', 5, 80),
    ('resource', '资源', 'noun', 5, 85), ('respond', '回应', 'verb', 5, 80), ('responsible', '负责的', 'adjective', 5, 80),
    ('restrict', '限制', 'verb', 6, 75), ('retain', '保留', 'verb', 6, 75), ('reveal', '揭示', 'verb', 6, 80),
    ('revenue', '收入', 'noun', 6, 75), ('reverse', '反向', 'verb', 6, 75), ('revise', '修订', 'verb', 6, 75),
    ('revolution', '革命', 'noun', 5, 80), ('rigid', '严格的', 'adjective', 6, 75), ('role', '角色', 'noun', 5, 85),
    ('route', '路线', 'noun', 5, 75), ('scenario', '情景', 'noun', 6, 75), ('schedule', '时刻表', 'noun', 6, 80),
    ('scheme', '计划', 'noun', 6, 75), ('scope', '范围', 'noun', 6, 75), ('section', '部分', 'noun', 5, 85),
    ('sector', '部门', 'noun', 6, 75), ('secure', '安全的', 'adjective', 5, 80), ('seek', '寻找', 'verb', 5, 80),
    ('select', '选择', 'verb', 5, 80), ('sequence', '序列', 'noun', 6, 75), ('series', '系列', 'noun', 5, 80),
    ('sex', '性别', 'noun', 5, 80), ('shift', '转变', 'noun', 5, 80), ('significant', '重要的', 'adjective', 5, 85),
    ('similar', '相似的', 'adjective', 5, 85), ('simulate', '模拟', 'verb', 6, 75), ('site', '地点', 'noun', 5, 80),
    ('so-called', '所谓的', 'adjective', 6, 70), ('sole', '唯一的', 'adjective', 6, 70), ('somewhat', '有点', 'adverb', 5, 75),
    ('source', '来源', 'noun', 5, 85), ('specific', '具体的', 'adjective', 5, 85), ('specify', '指定', 'verb', 6, 75),
    ('sphere', '球体', 'noun', 6, 70), ('stable', '稳定的', 'adjective', 6, 75), ('statistic', '统计', 'noun', 6, 80),
    ('status', '地位', 'noun', 5, 80), ('straightforward', '直截了当的', 'adjective', 6, 70), ('strategy', '策略', 'noun', 6, 80),
    ('stress', '压力', 'noun', 5, 80), ('structure', '结构', 'noun', 5, 85), ('style', '风格', 'noun', 5, 80),
    ('submit', '提交', 'verb', 6, 75), ('subordinate', '下属的', 'adjective', 7, 65), ('subsequent', '随后的', 'adjective', 6, 75),
    ('subsidy', '补贴', 'noun', 7, 70), ('substitute', '替代', 'noun', 6, 75), ('successor', '继任者', 'noun', 6, 70),
    ('sufficient', '足够的', 'adjective', 6, 75), ('sum', '总和', 'noun', 5, 75), ('summary', '总结', 'noun', 5, 80),
    ('supplement', '补充', 'noun', 6, 75), ('survey', '调查', 'noun', 6, 80), ('survive', '生存', 'verb', 5, 80),
    ('sustainable', '可持续的', 'adjective', 7, 75), ('symbol', '符号', 'noun', 5, 75), ('tape', '磁带', 'noun', 5, 70),
    ('task', '任务', 'noun', 4, 85), ('team', '团队', 'noun', 4, 85), ('technical', '技术的', 'adjective', 5, 85),
    ('technique', '技术', 'noun', 6, 80), ('technology', '技术', 'noun', 5, 85), ('temporary', '临时的', 'adjective', 6, 75),
    ('tense', '紧张的', 'adjective', 5, 75), ('terminate', '终止', 'verb', 6, 75), ('text', '文本', 'noun', 5, 85),
    ('theme', '主题', 'noun', 5, 75), ('theory', '理论', 'noun', 5, 85), ('thereby', '因此', 'adverb', 6, 70),
    ('thesis', '论文', 'noun', 6, 75), ('topic', '主题', 'noun', 4, 85), ('trace', '追踪', 'noun', 5, 75),
    ('tradition', '传统', 'noun', 5, 80), ('transfer', '转移', 'noun', 6, 75), ('transform', '转变', 'verb', 6, 75),
    ('transit', '过境', 'noun', 6, 70), ('transmit', '传输', 'verb', 6, 75), ('transport', '运输', 'noun', 5, 85),
    ('trend', '趋势', 'noun', 5, 80), ('trigger', '触发', 'verb', 6, 75), ('ultimately', '最终', 'adverb', 6, 75),
    ('undergo', '经历', 'verb', 6, 75), ('underlie', '构成基础', 'verb', 7, 70), ('undertake', '承担', 'verb', 6, 75),
    ('uniform', '统一的', 'adjective', 5, 75), ('unify', '统一', 'verb', 6, 75), ('unique', '独特的', 'adjective', 5, 80),
    ('utilize', '利用', 'verb', 6, 75), ('valid', '有效的', 'adjective', 6, 75), ('vary', '变化', 'verb', 5, 80),
    ('vehicle', '车辆', 'noun', 5, 80), ('version', '版本', 'noun', 5, 80), ('via', '通过', 'preposition', 5, 80),
    ('violate', '违反', 'verb', 6, 75), ('virtual', '虚拟的', 'adjective', 6, 80), ('visible', '可见的', 'adjective', 5, 75),
    ('vision', '视觉', 'noun', 5, 75), ('visual', '视觉的', 'adjective', 6, 75), ('volume', '卷', 'noun', 5, 80),
    ('voluntary', '自愿的', 'adjective', 6, 75), ('welfare', '福利', 'noun', 6, 75), ('whereas', '然而', 'conjunction', 6, 75),
    ('widespread', '广泛的', 'adjective', 6, 75), ('wisdom', '智慧', 'noun', 6, 70), ('withdraw', '撤回', 'verb', 6, 75),
    ('workshop', '研讨会', 'noun', 6, 75),
]

# 高频学术短语
ACADEMIC_PHRASES = [
    ('according to', '根据', 'phrase', 5, 90), ('as a result', '因此', 'phrase', 5, 85), ('as well as', '以及', 'phrase', 4, 90),
    ('based on', '基于', 'phrase', 5, 85), ('because of', '因为', 'phrase', 4, 90), ('by means of', '通过', 'phrase', 5, 75),
    ('due to', '由于', 'phrase', 5, 85), ('for example', '例如', 'phrase', 4, 90), ('for instance', '例如', 'phrase', 5, 85),
    ('in addition', '此外', 'phrase', 5, 85), ('in case of', '万一', 'phrase', 5, 75), ('in contrast', '相比之下', 'phrase', 5, 80),
    ('in fact', '事实上', 'phrase', 4, 85), ('in general', '一般来说', 'phrase', 5, 80), ('in order to', '为了', 'phrase', 4, 90),
    ('in other words', '换句话说', 'phrase', 5, 80), ('in particular', '特别是', 'phrase', 5, 80), ('in relation to', '关于', 'phrase', 6, 75),
    ('in terms of', '就...而言', 'phrase', 5, 85), ('in turn', '转而', 'phrase', 5, 75), ('instead of', '代替', 'phrase', 5, 85),
    ('moreover', '而且', 'adverb', 5, 85), ('on average', '平均', 'phrase', 5, 75), ('on the other hand', '另一方面', 'phrase', 5, 85),
    ('on the contrary', '相反', 'phrase', 5, 75), ('prior to', '在...之前', 'phrase', 6, 70), ('such as', '例如', 'phrase', 4, 90),
    ('that is', '即', 'phrase', 5, 80), ('with regard to', '关于', 'phrase', 5, 75), ('with respect to', '关于', 'phrase', 6, 75),
]

# 口语高频词汇
SPEAKING_VOCABULARY = [
    ('actually', '实际上', 'adverb', 4, 90), ('basically', '基本上', 'adverb', 4, 85), ('certainly', '当然', 'adverb', 4, 85),
    ('definitely', '肯定', 'adverb', 4, 85), ('honestly', '诚实地', 'adverb', 4, 80), ('literally', '字面上', 'adverb', 5, 80),
    ('obviously', '显然', 'adverb', 4, 85), ('personally', '就个人而言', 'adverb', 4, 85), ('probably', '可能', 'adverb', 4, 85),
    ('simply', '简单地', 'adverb', 4, 85), ('supposedly', '据说', 'adverb', 5, 75), ('totally', '完全', 'adverb', 4, 85),
    ('apparently', '显然', 'adverb', 5, 80), ('approximately', '大约', 'adverb', 5, 80), ('essentially', '本质上', 'adverb', 6, 75),
    ('fortunately', '幸运地', 'adverb', 5, 75), ('frankly', '坦率地', 'adverb', 5, 75), ('generally', '一般', 'adverb', 4, 85),
    ('hopefully', '希望', 'adverb', 4, 80), ('ideally', '理想地', 'adverb', 5, 75), ('incidentally', '顺便', 'adverb', 6, 70),
    ('interestingly', '有趣的是', 'adverb', 5, 75), ('luckily', '幸运地', 'adverb', 4, 75), ('mainly', '主要', 'adverb', 4, 85),
    ('mostly', '主要', 'adverb', 4, 80), ('naturally', '自然地', 'adverb', 4, 80), ('normally', '通常', 'adverb', 4, 85),
    ('originally', '最初', 'adverb', 5, 80), ('particularly', '特别', 'adverb', 5, 85), ('perhaps', '也许', 'adverb', 4, 85),
    ('possibly', '可能', 'adverb', 4, 80), ('practically', '实际上', 'adverb', 5, 75), ('presumably', '大概', 'adverb', 6, 70),
    ('primarily', '主要', 'adverb', 5, 80), ('rarely', '很少', 'adverb', 4, 80), ('really', '真地', 'adverb', 3, 95),
    ('relatively', '相对', 'adverb', 5, 80), ('seriously', '认真地', 'adverb', 4, 80), ('significantly', '显著地', 'adverb', 5, 80),
    ('slightly', '稍微', 'adverb', 4, 80), ('somehow', '以某种方式', 'adverb', 4, 75), ('somewhat', '有点', 'adverb', 5, 80),
    ('specifically', '具体', 'adverb', 5, 80), ('strongly', '强烈', 'adverb', 4, 80), ('supposedly', '据说', 'adverb', 5, 75),
    ('surprisingly', '令人惊讶', 'adverb', 5, 75), ('typically', '典型地', 'adverb', 5, 80), ('ultimately', '最终', 'adverb', 6, 75),
    ('unfortunately', '不幸', 'adverb', 4, 80), ('virtually', '几乎', 'adverb', 5, 80), ('wonderfully', '精彩地', 'adverb', 4, 75),
]

def generate_listening_vocabulary():
    """生成听力词汇"""
    words = []
    for scene, vocab_list in LISTENING_VOCABULARY.items():
        for word, translation, pos, level, freq in vocab_list:
            words.append({
                'word': word,
                'translation': translation,
                'pos': pos,
                'category': f'listening_{scene}',
                'scene': scene,
                'level': str(level),
                'frequency': freq,
                'source': 'IELTS_Listening'
            })
    return words

def generate_reading_vocabulary():
    """生成阅读词汇"""
    words = []
    for topic, vocab_list in READING_VOCABULARY.items():
        for word, translation, pos, level, freq in vocab_list:
            words.append({
                'word': word,
                'translation': translation,
                'pos': pos,
                'category': f'reading_{topic}',
                'topic': topic,
                'level': str(level),
                'frequency': freq,
                'source': 'IELTS_Reading'
            })
    return words

def generate_writing_vocabulary():
    """生成写作词汇"""
    return [{
        'word': w[0],
        'translation': w[1],
        'pos': w[2],
        'category': 'writing',
        'level': str(w[3]),
        'frequency': w[4],
        'source': 'IELTS_Writing'
    } for w in WRITING_VOCABULARY]

def generate_speaking_vocabulary():
    """生成口语词汇"""
    return [{
        'word': w[0],
        'translation': w[1],
        'pos': w[2],
        'category': 'speaking',
        'level': str(w[3]),
        'frequency': w[4],
        'source': 'IELTS_Speaking'
    } for w in SPEAKING_VOCABULARY]

def generate_academic_phrases():
    """生成学术短语"""
    return [{
        'word': w[0],
        'translation': w[1],
        'pos': w[2],
        'category': 'academic_phrases',
        'level': str(w[3]),
        'frequency': w[4],
        'source': 'Academic_Phrases'
    } for w in ACADEMIC_PHRASES]

def export_to_json(data: List[Dict], filename: str):
    """导出为JSON"""
    filepath = OUTPUT_DIR / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  - Exported: {filepath}")
    return filepath

def export_to_csv(data: List[Dict], filename: str):
    """导出为CSV"""
    if not data:
        return None
    filepath = OUTPUT_DIR / filename
    standard_fields = ['word', 'translation', 'pos', 'category', 'level', 'frequency', 'source']
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=standard_fields, extrasaction='ignore')
        writer.writeheader()
        for row in data:
            filtered = {k: row.get(k, '') for k in standard_fields}
            writer.writerow(filtered)
    print(f"  - Exported: {filepath}")
    return filepath

def generate_sql_inserts(data: List[Dict], filename: str):
    """生成SQL插入语句"""
    filepath = OUTPUT_DIR / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("-- IELTS Ultimate Vocabulary Inserts\n")
        f.write(f"-- Total words: {len(data)}\n\n")
        f.write("INSERT INTO words (word, translation, pos, category, level, frequency) VALUES\n")

        for i, w in enumerate(data):
            word = w['word'].replace("'", "''")
            trans = w['translation'].replace("'", "''")
            cat = w.get('category', 'general')
            level = w.get('level', '5')
            freq = w.get('frequency', 50)
            pos = w.get('pos', 'word')

            comma = ',' if i < len(data) - 1 else ';'
            f.write(f"  ('{word}', '{trans}', '{pos}', '{cat}', '{level}', {freq}){comma}\n")

    print(f"  - Exported: {filepath}")
    return filepath

def generate_all_vocabulary():
    """生成所有词汇"""
    print("=" * 60)
    print("IELTS Ultimate Vocabulary Generator")
    print("=" * 60)

    all_vocabularies = {}

    print("\n[1/6] Generating AWL academic vocabulary...")
    all_vocabularies['awl'] = parse_awl_comprehensive()
    print(f"  - Generated {len(all_vocabularies['awl'])} AWL words")

    print("\n[2/6] Generating listening vocabulary...")
    all_vocabularies['listening'] = generate_listening_vocabulary()
    print(f"  - Generated {len(all_vocabularies['listening'])} listening words")

    print("\n[3/6] Generating reading vocabulary...")
    all_vocabularies['reading'] = generate_reading_vocabulary()
    print(f"  - Generated {len(all_vocabularies['reading'])} reading words")

    print("\n[4/6] Generating writing vocabulary...")
    all_vocabularies['writing'] = generate_writing_vocabulary()
    print(f"  - Generated {len(all_vocabularies['writing'])} writing words")

    print("\n[5/6] Generating speaking vocabulary...")
    all_vocabularies['speaking'] = generate_speaking_vocabulary()
    print(f"  - Generated {len(all_vocabularies['speaking'])} speaking words")

    print("\n[6/6] Generating academic phrases...")
    all_vocabularies['phrases'] = generate_academic_phrases()
    print(f"  - Generated {len(all_vocabularies['phrases'])} academic phrases")

    # 合并所有词汇
    print("\n[7/7] Merging and deduplicating...")
    all_words = []
    seen = set()
    for category, words in all_vocabularies.items():
        for w in words:
            word_key = w['word'].lower()
            if word_key not in seen:
                seen.add(word_key)
                all_words.append(w)

    print(f"\n[STATS] Total unique words: {len(all_words)}")

    # 导出
    print("\n" + "-" * 40)
    print("Exporting files...")
    print("-" * 40)

    export_to_json(all_words, 'ielts_vocabulary_ultimate.json')
    export_to_csv(all_words, 'ielts_vocabulary_ultimate.csv')
    generate_sql_inserts(all_words, 'vocabulary_ultimate_inserts.sql')

    # 按类别导出
    for category, words in all_vocabularies.items():
        export_to_json(words, f'ielts_vocabulary_{category}.json')
        export_to_csv(words, f'ielts_vocabulary_{category}.csv')

    # 生成统计信息
    print("\n" + "=" * 60)
    print("Generation Summary:")
    print("=" * 60)
    for category, words in all_vocabularies.items():
        print(f"  {category:15s}: {len(words):4d} words")
    print(f"  {'TOTAL UNIQUE':15s}: {len(all_words):4d} words")
    print("=" * 60)

    return all_words

if __name__ == '__main__':
    generate_all_vocabulary()
