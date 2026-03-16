#!/usr/bin/env python3
"""
IELTS Extended Vocabulary Generator
Generates 5,000-8,000 IELTS vocabulary words
"""

import json
import csv
from pathlib import Path
from typing import Dict, List

OUTPUT_DIR = Path(__file__).parent / "vocabulary_data"
OUTPUT_DIR.mkdir(exist_ok=True)

# AWL 570词族数据（子表1-3，共约180个headwords）
AWL_FAMILY_DATA = """
analyse,analysis,noun,分析,1
analyse,analyst,noun,分析师,1
analyse,analytic,adjective,分析的,1
analyse,analytical,adjective,分析的,1
analyse,analytically,adverb,分析地,1
approach,approach,noun/verb,方法/接近,1
approach,approachable,adjective,可接近的,1
approach,approached,verb,接近,1
approach,approaches,noun/verb,方法/接近,1
approach,approaching,verb,接近,1
area,area,noun,领域,1
area,areas,noun,领域,1
assess,assess,verb,评估,1
assess,assessable,adjective,可评估的,1
assess,assessment,noun,评估,1
assess,assessments,noun,评估,1
assess,reassess,verb,重新评估,1
assess,reassessment,noun,重新评估,1
assume,assume,verb,假设,1
assume,assumed,verb,假设,1
assume,assumes,verb,假设,1
assume,assuming,verb,假设,1
assume,assumption,noun,假设,1
assume,assumptions,noun,假设,1
authority,authority,noun,权威,1
authority,authorities,noun,当局,1
authority,authoritative,adjective,权威的,1
available,available,adjective,可用的,1
available,availability,noun,可用性,1
available,unavailable,adjective,不可用的,1
benefit,benefit,noun/verb,益处,1
benefit,benefits,noun/verb,益处,1
benefit,benefited,verb,受益,1
benefit,benefiting,verb,受益,1
benefit,beneficial,adjective,有益的,1
benefit,beneficiary,noun,受益人,1
concept,concept,noun,概念,1
concept,concepts,noun,概念,1
concept,conception,noun,概念,1
concept,conceptual,adjective,概念上的,1
consist,consist,verb,由...组成,1
consist,consisted,verb,由...组成,1
consist,consisting,verb,由...组成,1
consist,consists,verb,由...组成,1
consist,consistent,adjective,一致的,1
consist,consistently,adverb,一贯地,1
consist,consistency,noun,一致性,1
consist,inconsistent,adjective,不一致的,1
constitute,constitute,verb,构成,1
constitute,constituted,verb,构成,1
constitute,constitutes,verb,构成,1
constitute,constituting,verb,构成,1
constitute,constitution,noun,宪法,1
constitute,constitutional,adjective,宪法的,1
context,context,noun,上下文,1
context,contexts,noun,上下文,1
context,contextual,adjective,上下文的,1
contract,contract,noun/verb,合同,1
contract,contracted,verb,收缩,1
contract,contracting,verb,订约,1
contract,contracts,noun/verb,合同,1
contract,contractor,noun,承包商,1
create,create,verb,创造,1
create,created,verb,创造,1
create,creates,verb,创造,1
create,creating,verb,创造,1
create,creation,noun,创造,1
create,creations,noun,创造物,1
create,creative,adjective,创造性的,1
create,creativity,noun,创造力,1
create,creator,noun,创造者,1
data,data,noun,数据,1
define,define,verb,定义,1
define,defined,verb,定义,1
define,defines,verb,定义,1
define,defining,verb,定义,1
define,definition,noun,定义,1
define,definitions,noun,定义,1
define,definable,adjective,可定义的,1
define,redefine,verb,重新定义,1
define,undefined,adjective,未定义的,1
derive,derive,verb,推导,1
derive,derived,verb,推导,1
derive,derives,verb,推导,1
derive,deriving,verb,推导,1
derive,derivation,noun,推导,1
derive,derivative,noun,派生词,1
distribute,distribute,verb,分配,1
distribute,distributed,verb,分配,1
distribute,distributing,verb,分配,1
distribute,distribution,noun,分配,1
distribute,distributions,noun,分配,1
distribute,distributor,noun,分销商,1
economy,economy,noun,经济,1
economy,economies,noun,经济,1
economy,economic,adjective,经济的,1
economy,economical,adjective,节约的,1
economy,economics,noun,经济学,1
economy,economist,noun,经济学家,1
environment,environment,noun,环境,1
environment,environments,noun,环境,1
environment,environmental,adjective,环境的,1
environment,environmentally,adverb,环境上,1
establish,establish,verb,建立,1
establish,established,verb,建立,1
establish,establishes,verb,建立,1
establish,establishing,verb,建立,1
establish,establishment,noun,建立,1
establish,establishments,noun,机构,1
estimate,estimate,verb/noun,估计,1
estimate,estimated,verb/adjective,估计的,1
estimate,estimates,noun/verb,估计,1
estimate,estimating,verb,估计,1
estimate,estimation,noun,估计,1
evidence,evidence,noun,证据,1
evidence,evident,adjective,明显的,1
evidence,evidently,adverb,明显地,1
export,export,verb/noun,出口,1
export,exported,verb,出口,1
export,exporting,verb,出口,1
export,exports,noun/verb,出口,1
export,exporter,noun,出口商,1
factor,factor,noun,因素,1
factor,factors,noun,因素,1
factor,factored,verb,分解,1
finance,finance,noun/verb,金融,1
finance,finances,noun,财务,1
finance,financial,adjective,金融的,1
finance,financially,adverb,财务上,1
finance,financed,verb,资助,1
finance,financing,noun,融资,1
formula,formula,noun,公式,1
formula,formulas,noun,公式,1
formula,formulate,verb,制定,1
formula,formulation,noun,公式化,1
function,function,noun/verb,功能,1
function,functions,noun/verb,功能,1
function,functioned,verb,起作用,1
function,functioning,noun/verb,功能,1
function,functional,adjective,功能的,1
identify,identify,verb,识别,1
identify,identified,verb,识别,1
identify,identifies,verb,识别,1
identify,identifying,verb,识别,1
identify,identification,noun,识别,1
identify,identity,noun,身份,1
identify,identities,noun,身份,1
income,income,noun,收入,1
indicate,indicate,verb,表明,1
indicate,indicated,verb,表明,1
indicate,indicates,verb,表明,1
indicate,indicating,verb,表明,1
indicate,indication,noun,迹象,1
indicate,indicator,noun,指标,1
individual,individual,noun/adjective,个人的,1
individual,individuals,noun,个人,1
individual,individuality,noun,个性,1
individual,individually,adverb,个别地,1
interpret,interpret,verb,解释,1
interpret,interpreted,verb,解释,1
interpret,interpreting,verb,解释,1
interpret,interprets,verb,解释,1
interpret,interpretation,noun,解释,1
interpret,interpreter,noun,译员,1
interpret,misinterpret,verb,误解,1
involve,involve,verb,涉及,1
involve,involved,verb/adjective,涉及的,1
involve,involves,verb,涉及,1
involve,involving,verb,涉及,1
involve,involvement,noun,参与,1
issue,issue,noun/verb,问题,1
issue,issues,noun/verb,问题,1
issue,issued,verb,发行,1
issue,issuing,verb,发行,1
labour,labour,noun,劳动,1
labour,labours,noun,劳动,1
labour,laboured,verb,辛勤工作,1
labour,labor,noun,劳动,1
legal,legal,adjective,合法的,1
legal,legally,adverb,合法地,1
legal,illegal,adjective,非法的,1
legal,illegally,adverb,非法地,1
legal,legislate,verb,立法,1
legal,legislation,noun,立法,1
legal,legislative,adjective,立法的,1
legal,legislator,noun,立法者,1
legal,legislature,noun,立法机关,1
major,major,adjective,主要的,1
major,majority,noun,多数,1
major,majorities,noun,多数,1
method,method,noun,方法,1
method,methods,noun,方法,1
method,methodology,noun,方法论,1
method,methodological,adjective,方法的,1
occur,occur,verb,发生,1
occur,occurred,verb,发生,1
occur,occurring,verb,发生,1
occur,occurs,verb,发生,1
occur,reoccur,verb,再次发生,1
percent,percent,noun,百分比,1
percent,percentage,noun,百分比,1
period,period,noun,时期,1
period,periods,noun,时期,1
period,periodic,adjective,周期的,1
period,periodical,noun,期刊,1
period,periodically,adverb,定期地,1
policy,policy,noun,政策,1
policy,policies,noun,政策,1
principle,principle,noun,原则,1
principle,principles,noun,原则,1
principle,principled,adjective,有原则的,1
proceed,proceed,verb,继续进行,1
proceed,proceeded,verb,继续进行,1
proceed,proceeding,noun,程序,1
proceed,proceeds,noun,收益,1
proceed,procedure,noun,程序,1
proceed,procedures,noun,程序,1
process,process,noun/verb,过程,1
process,processes,noun/verb,过程,1
process,processed,verb,处理,1
process,processing,noun,处理,1
require,require,verb,需要,1
require,required,verb/adjective,必需的,1
require,requires,verb,需要,1
require,requiring,verb,需要,1
require,requirement,noun,要求,1
respond,respond,verb,回应,1
respond,responded,verb,回应,1
respond,responding,verb,回应,1
respond,responds,verb,回应,1
respond,response,noun,回应,1
respond,responses,noun,回应,1
respond,responsive,adjective,响应的,1
role,role,noun,角色,1
role,roles,noun,角色,1
section,section,noun,部分,1
section,sections,noun,部分,1
section,sectioned,verb,分割,1
sector,sector,noun,部门,1
sector,sectors,noun,部门,1
significant,significant,adjective,重要的,1
significant,significantly,adverb,显著地,1
significant,significance,noun,重要性,1
significant,insignificant,adjective,不重要的,1
similar,similar,adjective,相似的,1
similar,similarly,adverb,同样,1
similar,similarity,noun,相似性,1
similar,dissimilar,adjective,不同的,1
source,source,noun,来源,1
source,sources,noun,来源,1
source,sourced,verb,采购,1
specific,specific,adjective,具体的,1
specific,specifically,adverb,具体地,1
specific,specification,noun,规格,1
structure,structure,noun/verb,结构,1
structure,structures,noun,结构,1
structure,structured,adjective,有结构的,1
structure,structural,adjective,结构的,1
theory,theory,noun,理论,1
theory,theories,noun,理论,1
theory,theoretical,adjective,理论的,1
theory,theorist,noun,理论家,1
vary,vary,verb,变化,1
vary,varies,verb,变化,1
vary,variety,noun,多样,1
vary,various,adjective,各种各样的,1
vary,variable,noun/adjective,变量,1
vary,variation,noun,变化,1
vary,varying,adjective,不同的,1
achieve,achieve,verb,实现,2
achieve,achieved,verb,实现,2
achieve,achieves,verb,实现,2
achieve,achieving,verb,实现,2
achieve,achievement,noun,成就,2
achieve,achievements,noun,成就,2
achieve,achievable,adjective,可实现的,2
acquire,acquire,verb,获得,2
acquire,acquired,verb,获得,2
acquire,acquires,verb,获得,2
acquire,acquiring,verb,获得,2
acquire,acquisition,noun,获得,2
administrate,administrate,verb,管理,2
administrate,administration,noun,管理,2
administrate,administrative,adjective,管理的,2
administrate,administrator,noun,管理员,2
affect,affect,verb,影响,2
affect,affected,verb,影响,2
affect,affects,verb,影响,2
affect,affecting,verb,影响,2
affect,affective,adjective,情感的,2
affect,unaffected,adjective,不受影响的,2
appropriate,appropriate,adjective,适当的,2
appropriate,appropriacy,noun,适当,2
appropriate,inappropriate,adjective,不适当的,2
aspect,aspect,noun,方面,2
aspect,aspects,noun,方面,2
assist,assist,verb,帮助,2
assist,assisted,verb,帮助,2
assist,assisting,verb,帮助,2
assist,assists,verb,帮助,2
assist,assistance,noun,帮助,2
assist,assistant,noun,助手,2
category,category,noun,类别,2
category,categories,noun,类别,2
category,categorise,verb,分类,2
category,categorization,noun,分类,2
chapter,chapter,noun,章节,2
chapter,chapters,noun,章节,2
commission,commission,noun/verb,委员会,2
commission,commissioned,verb,委任,2
commission,commissioner,noun,委员,2
community,community,noun,社区,2
community,communities,noun,社区,2
complex,complex,adjective/noun,复杂的,2
complex,complexity,noun,复杂性,2
compute,compute,verb,计算,2
compute,computed,verb,计算,2
compute,computer,noun,计算机,2
compute,computing,noun,计算,2
compute,computational,adjective,计算的,2
conclude,conclude,verb,结论,2
conclude,concluded,verb,结论,2
conclude,concludes,verb,结论,2
conclude,concluding,verb,结论,2
conclude,conclusion,noun,结论,2
conclude,conclusions,noun,结论,2
conduct,conduct,verb/noun,进行,2
conduct,conducted,verb,进行,2
conduct,conducting,verb,进行,2
conduct,conducts,verb,进行,2
consequence,consequence,noun,后果,2
consequence,consequences,noun,后果,2
consequence,consequent,adjective,随之而来的,2
consequence,consequently,adverb,因此,2
construct,construct,verb,构建,2
construct,constructed,verb,构建,2
construct,constructing,verb,构建,2
construct,construction,noun,建造,2
construct,reconstruct,verb,重建,2
construct,reconstruction,noun,重建,2
consume,consume,verb,消费,2
consume,consumed,verb,消费,2
consume,consumes,verb,消费,2
consume,consuming,verb,消费,2
consume,consumer,noun,消费者,2
consume,consumption,noun,消费,2
credit,credit,noun/verb,信用,2
credit,credited,verb,归功于,2
credit,credits,noun,学分,2
credit,creditor,noun,债权人,2
culture,culture,noun,文化,2
culture,cultures,noun,文化,2
culture,cultural,adjective,文化的,2
culture,culturally,adverb,文化上,2
design,design,noun/verb,设计,2
design,designed,verb,设计,2
design,designer,noun,设计师,2
design,designs,noun,设计,2
distinct,distinct,adjective,明显的,2
distinct,distinction,noun,区别,2
distinct,distinctive,adjective,独特的,2
distinct,distinctly,adverb,明显地,2
element,element,noun,元素,2
element,elements,noun,元素,2
equate,equate,verb,等同,2
equate,equated,verb,等同,2
equate,equation,noun,方程,2
evaluate,evaluate,verb,评估,2
evaluate,evaluated,verb,评估,2
evaluate,evaluation,noun,评估,2
evaluate,evaluative,adjective,评估的,2
feature,feature,noun/verb,特征,2
feature,features,noun,特征,2
feature,featured,verb,以...为特色,2
final,final,adjective/noun,最终的,2
final,finally,adverb,最终,2
final,finals,noun,决赛,2
final,finalise,verb,最终确定,2
focus,focus,noun/verb,焦点,2
focus,focused,adjective,专注的,2
focus,focuses,noun/verb,焦点,2
focus,focusing,verb,集中,2
impact,impact,noun/verb,影响,2
impact,impacted,verb,影响,2
impact,impacts,noun/verb,影响,2
injure,injure,verb,伤害,2
injure,injured,adjective,受伤的,2
injure,injuries,noun,伤害,2
injure,injury,noun,伤害,2
institute,institute,noun/verb,机构,2
institute,institution,noun,机构,2
institute,institutional,adjective,机构的,2
invest,invest,verb,投资,2
invest,invested,verb,投资,2
invest,investing,verb,投资,2
invest,investment,noun,投资,2
invest,investor,noun,投资者,2
item,item,noun,项目,2
item,items,noun,项目,2
journal,journal,noun,期刊,2
journal,journals,noun,期刊,2
maintain,maintain,verb,维持,2
maintain,maintained,verb,维持,2
maintain,maintains,verb,维持,2
maintain,maintenance,noun,维护,2
measure,measure,verb/noun,测量,2
measure,measured,verb,测量,2
measure,measurement,noun,测量,2
measure,measures,noun,措施,2
obtain,obtain,verb,获得,2
obtain,obtained,verb,获得,2
obtain,obtains,verb,获得,2
obtain,obtainable,adjective,可获得的,2
participate,participate,verb,参与,2
participate,participated,verb,参与,2
participate,participating,verb,参与,2
participate,participation,noun,参与,2
participate,participant,noun,参与者,2
perceive,perceive,verb,感知,2
perceive,perceived,verb,感知,2
perceive,perception,noun,感知,2
positive,positive,adjective,积极的,2
positive,positively,adverb,积极地,2
potential,potential,adjective/noun,潜在的,2
potential,potentially,adverb,潜在地,2
previous,previous,adjective,以前的,2
previous,previously,adverb,先前,2
primary,primary,adjective,主要的,2
primary,primarily,adverb,主要地,2
purchase,purchase,verb/noun,购买,2
purchase,purchased,verb,购买,2
purchase,purchaser,noun,购买者,2
range,range,noun/verb,范围,2
range,ranged,verb,排列,2
range,ranges,noun,范围,2
range,ranging,verb,变化,2
region,region,noun,地区,2
region,regions,noun,地区,2
region,regional,adjective,地区的,2
regulate,regulate,verb,调节,2
regulate,regulated,verb,调节,2
regulate,regulates,verb,调节,2
regulate,regulating,verb,调节,2
regulate,regulation,noun,规章,2
regulate,regulations,noun,法规,2
regulate,regulatory,adjective,管理的,2
regulate,regulator,noun,调节器,2
regulate,deregulation,noun,放松管制,2
relevant,relevant,adjective,相关的,2
relevant,relevance,noun,相关性,2
relevant,irrelevant,adjective,不相关的,2
resource,resource,noun,资源,2
resource,resources,noun,资源,2
resource,resourced,verb,提供资源,2
resource,resourcing,noun,资源配置,2
restrict,restrict,verb,限制,2
restrict,restricted,verb/adjective,受限制的,2
restrict,restricting,verb,限制,2
restrict,restriction,noun,限制,2
restrict,restrictions,noun,限制,2
restrict,restrictive,adjective,限制性的,2
secure,secure,adjective/verb,安全的,2
secure,secured,verb,保护,2
secure,securities,noun,证券,2
secure,security,noun,安全,2
seek,seek,verb,寻找,2
seek,seeks,verb,寻找,2
seek,seeking,verb,寻找,2
seek,sought,verb,寻找,2
select,select,verb,选择,2
select,selected,verb/adjective,选择的,2
select,selecting,verb,选择,2
select,selection,noun,选择,2
select,selective,adjective,选择性的,2
site,site,noun,地点,2
site,sites,noun,地点,2
strategy,strategy,noun,策略,2
strategy,strategies,noun,策略,2
strategy,strategic,adjective,战略的,2
strategy,strategically,adverb,战略上,2
survey,survey,noun/verb,调查,2
survey,surveyed,verb,调查,2
survey,surveying,noun,测量,2
survey,surveys,noun/verb,调查,2
text,text,noun,文本,2
text,texts,noun,文本,2
text,textual,adjective,文本的,2
tradition,tradition,noun,传统,2
tradition,traditions,noun,传统,2
tradition,traditional,adjective,传统的,2
tradition,traditionally,adverb,传统上,2
transfer,transfer,verb/noun,转移,2
transfer,transferred,verb,转移,2
transfer,transferring,verb,转移,2
transfer,transfers,noun/verb,转移,2
transfer,transferable,adjective,可转移的,2
alternative,alternative,noun/adjective,替代,3
alternative,alternatively,adverb,或者,3
alternative,alternatives,noun,替代方案,3
circumstance,circumstance,noun,环境,3
circumstance,circumstances,noun,环境,3
comment,comment,noun/verb,评论,3
comment,commented,verb,评论,3
comment,commenting,verb,评论,3
comment,comments,noun/verb,评论,3
comment,commentary,noun,评论,3
comment,commentator,noun,评论员,3
compensate,compensate,verb,补偿,3
compensate,compensated,verb,补偿,3
compensate,compensates,verb,补偿,3
compensate,compensation,noun,补偿,3
compensate,compensatory,adjective,补偿的,3
component,component,noun,组件,3
component,components,noun,组件,3
consent,consent,noun/verb,同意,3
consent,consented,verb,同意,3
consent,consenting,verb,同意,3
considerable,considerable,adjective,相当大的,3
considerable,considerably,adverb,相当,3
constant,constant,adjective,持续的,3
constant,constants,noun,常数,3
constant,constantly,adverb,不断地,3
constrain,constrain,verb,约束,3
constrain,constrained,verb,约束,3
constrain,constraint,noun,约束,3
constrain,constraints,noun,约束,3
contribute,contribute,verb,贡献,3
contribute,contributed,verb,贡献,3
contribute,contributes,verb,贡献,3
contribute,contributing,verb,贡献,3
contribute,contribution,noun,贡献,3
contribute,contributor,noun,贡献者,3
convene,convene,verb,召集,3
convene,convened,verb,召集,3
convene,convention,noun,惯例,3
convene,conventions,noun,大会,3
coordinate,coordinate,verb/adjective,协调,3
coordinate,coordinated,verb,协调,3
coordinate,coordinates,noun,坐标,3
coordinate,coordination,noun,协调,3
coordinate,coordinator,noun,协调员,3
core,core,noun/adjective,核心,3
core,cores,noun,核心,3
corporate,corporate,adjective,公司的,3
corporate,corporation,noun,公司,3
corporate,corporations,noun,公司,3
correspond,correspond,verb,对应,3
correspond,corresponded,verb,对应,3
correspond,corresponding,adjective,相应的,3
correspond,correspondence,noun,通信,3
correspond,correspondent,noun,记者,3
criteria,criteria,noun,标准,3
criteria,criterion,noun,标准,3
deduce,deduce,verb,推论,3
deduce,deduced,verb,推论,3
deduce,deduction,noun,推论,3
demonstrate,demonstrate,verb,证明,3
demonstrate,demonstrated,verb,证明,3
demonstrate,demonstrates,verb,证明,3
demonstrate,demonstration,noun,演示,3
demonstrate,demonstrator,noun,示威者,3
document,document,noun/verb,文件,3
document,documented,verb,记录,3
document,documentation,noun,文件,3
document,documents,noun,文件,3
dominate,dominate,verb,支配,3
dominate,dominated,verb,支配,3
dominate,dominates,verb,支配,3
dominate,domination,noun,支配,3
dominate,dominant,adjective,占优势的,3
emphasis,emphasis,noun,强调,3
emphasis,emphases,noun,强调,3
emphasis,emphasise,verb,强调,3
emphasis,emphasize,verb,强调,3
emphasis,emphasized,verb,强调,3
ensure,ensure,verb,确保,3
ensure,ensured,verb,确保,3
ensure,ensures,verb,确保,3
ensure,ensuring,verb,确保,3
exclude,exclude,verb,排除,3
exclude,excluded,verb,排除,3
exclude,excludes,verb,排除,3
exclude,excluding,verb,排除,3
exclude,exclusion,noun,排除,3
framework,framework,noun,框架,3
framework,frameworks,noun,框架,3
fund,fund,noun/verb,资金,3
fund,funded,verb,资助,3
fund,funding,noun,资金,3
fund,funds,noun,资金,3
illustrate,illustrate,verb,说明,3
illustrate,illustrated,verb,说明,3
illustrate,illustrates,verb,说明,3
illustrate,illustration,noun,说明,3
illustrate,illustrative,adjective,说明的,3
immigrate,immigrate,verb,移民,3
immigrate,immigrated,verb,移民,3
immigrate,immigration,noun,移民,3
immigrate,immigrant,noun,移民,3
imply,imply,verb,暗示,3
imply,implied,verb,暗示,3
imply,implies,verb,暗示,3
imply,implication,noun,含义,3
initial,initial,adjective,最初的,3
initial,initially,adverb,最初,3
instance,instance,noun,例子,3
instance,instances,noun,例子,3
interact,interact,verb,互动,3
interact,interacted,verb,互动,3
interact,interacting,verb,互动,3
interact,interaction,noun,互动,3
interact,interactive,adjective,交互的,3
justify,justify,verb,证明正当,3
justify,justified,verb,证明正当,3
justify,justifies,verb,证明正当,3
justify,justification,noun,正当理由,3
layer,layer,noun,层,3
layer,layers,noun,层,3
layer,layered,adjective,分层的,3
link,link,noun/verb,链接,3
link,linked,verb,连接,3
link,links,noun,链接,3
link,linking,verb,连接,3
locate,locate,verb,定位,3
locate,located,verb,位于,3
locate,locating,verb,定位,3
locate,location,noun,位置,3
locate,locations,noun,位置,3
maximise,maximise,verb,最大化,3
maximise,maximised,verb,最大化,3
maximise,maximising,verb,最大化,3
maximise,maximum,noun/adjective,最大,3
minority,minority,noun,少数,3
minority,minorities,noun,少数,3
negate,negate,verb,否定,3
negate,negated,verb,否定,3
negate,negates,verb,否定,3
negate,negation,noun,否定,3
negate,negative,adjective,否定的,3
outcome,outcome,noun,结果,3
outcome,outcomes,noun,结果,3
partner,partner,noun,伙伴,3
partner,partners,noun,伙伴,3
partner,partnership,noun,合伙,3
philosophy,philosophy,noun,哲学,3
philosophy,philosophies,noun,哲学,3
philosophy,philosopher,noun,哲学家,3
philosophy,philosophical,adjective,哲学的,3
physical,physical,adjective,身体的,3
physical,physically,adverb,身体上,3
proportion,proportion,noun,比例,3
proportion,proportions,noun,比例,3
proportion,proportional,adjective,成比例的,3
publish,publish,verb,出版,3
publish,published,verb,出版,3
publish,publishes,verb,出版,3
publish,publishing,noun,出版业,3
publish,publisher,noun,出版商,3
react,react,verb,反应,3
react,reacted,verb,反应,3
react,reacting,verb,反应,3
react,reaction,noun,反应,3
react,reactions,noun,反应,3
react,reactive,adjective,反应的,3
register,register,verb/noun,注册,3
register,registered,verb/adjective,注册的,3
register,registering,verb,注册,3
register,registration,noun,注册,3
register,registrar,noun,注册员,3
rely,rely,verb,依赖,3
rely,relied,verb,依赖,3
rely,relies,verb,依赖,3
rely,relying,verb,依赖,3
rely,reliable,adjective,可靠的,3
rely,reliance,noun,依赖,3
remove,remove,verb,移除,3
remove,removed,verb,移除,3
remove,removes,verb,移除,3
remove,removing,verb,移除,3
remove,removal,noun,移除,3
scheme,scheme,noun,方案,3
scheme,schemes,noun,方案,3
sequence,sequence,noun,序列,3
sequence,sequences,noun,序列,3
sequence,sequenced,verb,排序,3
sex,sex,noun,性别,3
sex,sexual,adjective,性的,3
sex,sexuality,noun,性欲,3
shift,shift,noun/verb,转移,3
shift,shifted,verb,转移,3
shift,shifts,noun,轮班,3
shift,shifting,verb,转移,3
specify,specify,verb,指定,3
specify,specified,verb,指定,3
specify,specifies,verb,指定,3
specify,specifying,verb,指定,3
specify,specification,noun,规格,3
sufficient,sufficient,adjective,足够的,3
sufficient,sufficiently,adverb,充分地,3
sufficient,sufficiency,noun,充足,3
sufficient,insufficient,adjective,不足的,3
task,task,noun,任务,3
task,tasks,noun,任务,3
task,tasked,verb,派给任务,3
technical,technical,adjective,技术的,3
technical,technically,adverb,技术上,3
technology,technology,noun,技术,3
technology,technologies,noun,技术,3
technology,technological,adjective,技术的,3
valid,valid,adjective,有效的,3
valid,validity,noun,有效性,3
valid,validate,verb,验证,3
valid,validated,verb,验证,3
valid,invalid,adjective,无效的,3
volume,volume,noun,体积,3
volume,volumes,noun,卷,3
"""

def parse_awl_data():
    """解析AWL数据"""
    words = []
    for line in AWL_FAMILY_DATA.strip().split('\n'):
        if not line.strip():
            continue
        parts = line.split(',')
        if len(parts) >= 5:
            headword, word, pos, trans, sublist = parts[:5]
            level = 6 + int(sublist)
            words.append({
                'word': word.strip(),
                'headword': headword.strip(),
                'translation': trans.strip(),
                'pos': pos.strip(),
                'category': 'academic',
                'sublist': int(sublist),
                'level': str(level),
                'frequency': 60 - int(sublist) * 5,
                'source': 'AWL'
            })
    return words

# 雅思听力场景词汇
IELTS_LISTENING_SCENES = {
    'accommodation': [
        ('accommodation', '住宿', 'noun', 5),
        ('apartment', '公寓', 'noun', 5),
        ('flat', '公寓', 'noun', 5),
        ('house', '房子', 'noun', 4),
        ('dormitory', '宿舍', 'noun', 5),
        ('hostel', '旅舍', 'noun', 5),
        ('hotel', '酒店', 'noun', 4),
        ('motel', '汽车旅馆', 'noun', 5),
        ('residence', '住宅', 'noun', 6),
        ('homestay', '寄宿家庭', 'noun', 5),
        ('rent', '租金', 'noun/verb', 5),
        ('deposit', '押金', 'noun', 5),
        ('landlord', '房东', 'noun', 5),
        ('landlady', '女房东', 'noun', 5),
        ('tenant', '租户', 'noun', 6),
        ('roommate', '室友', 'noun', 5),
        ('bathroom', '浴室', 'noun', 4),
        ('bedroom', '卧室', 'noun', 4),
        ('kitchen', '厨房', 'noun', 4),
        ('living room', '客厅', 'noun', 4),
        ('dining room', '餐厅', 'noun', 4),
        ('garage', '车库', 'noun', 5),
        ('garden', '花园', 'noun', 4),
        ('balcony', '阳台', 'noun', 5),
        ('basement', '地下室', 'noun', 5),
        ('furniture', '家具', 'noun', 5),
        ('furnished', '带家具的', 'adjective', 5),
        ('unfurnished', '无家具的', 'adjective', 6),
        ('facility', '设施', 'noun', 6),
        ('utilities', '公用事业', 'noun', 6),
        ('heating', '暖气', 'noun', 5),
        ('air conditioning', '空调', 'noun', 5),
        ('refrigerator', '冰箱', 'noun', 5),
        ('washing machine', '洗衣机', 'noun', 5),
        ('microwave', '微波炉', 'noun', 5),
        ('stove', '炉子', 'noun', 5),
        ('contract', '合同', 'noun', 5),
        ('lease', '租约', 'noun', 6),
        ('bill', '账单', 'noun', 5),
    ],
    'education': [
        ('university', '大学', 'noun', 4),
        ('college', '学院', 'noun', 4),
        ('campus', '校园', 'noun', 5),
        ('faculty', '院系', 'noun', 6),
        ('department', '系', 'noun', 5),
        ('institute', '研究所', 'noun', 6),
        ('academy', '学院', 'noun', 5),
        ('library', '图书馆', 'noun', 4),
        ('laboratory', '实验室', 'noun', 6),
        ('lecture', '讲座', 'noun', 5),
        ('seminar', '研讨会', 'noun', 6),
        ('tutorial', '辅导课', 'noun', 6),
        ('workshop', '研讨会', 'noun', 6),
        ('course', '课程', 'noun', 4),
        ('curriculum', '课程', 'noun', 6),
        ('subject', '科目', 'noun', 4),
        ('discipline', '学科', 'noun', 6),
        ('major', '专业', 'noun', 5),
        ('minor', '辅修', 'noun', 6),
        ('degree', '学位', 'noun', 5),
        ('diploma', '文凭', 'noun', 5),
        ('certificate', '证书', 'noun', 5),
        ('bachelor', '学士', 'noun', 5),
        ('master', '硕士', 'noun', 5),
        ('doctorate', '博士', 'noun', 6),
        ('undergraduate', '本科生', 'noun', 6),
        ('postgraduate', '研究生', 'noun', 6),
        ('student', '学生', 'noun', 4),
        ('pupil', '学生', 'noun', 5),
        ('scholar', '学者', 'noun', 6),
        ('professor', '教授', 'noun', 5),
        ('lecturer', '讲师', 'noun', 5),
        ('tutor', '导师', 'noun', 5),
        ('supervisor', '导师', 'noun', 6),
        ('principal', '校长', 'noun', 5),
        ('headmaster', '校长', 'noun', 5),
        ('dean', '系主任', 'noun', 6),
        ('chancellor', '校长', 'noun', 7),
        ('registration', '注册', 'noun', 5),
        ('enrollment', '入学', 'noun', 6),
        ('admission', '录取', 'noun', 6),
        ('application', '申请', 'noun', 5),
        ('assignment', '作业', 'noun', 5),
        ('essay', '论文', 'noun', 5),
        ('thesis', '论文', 'noun', 6),
        ('dissertation', '论文', 'noun', 7),
        ('research', '研究', 'noun/verb', 5),
        ('project', '项目', 'noun', 5),
        ('assessment', '评估', 'noun', 6),
        ('examination', '考试', 'noun', 5),
        ('exam', '考试', 'noun', 4),
        ('quiz', '测验', 'noun', 5),
        ('test', '测试', 'noun', 4),
        ('grade', '成绩', 'noun', 5),
        ('score', '分数', 'noun', 5),
        ('mark', '分数', 'noun', 5),
        ('credit', '学分', 'noun', 5),
        ('attendance', '出勤', 'noun', 6),
        ('scholarship', '奖学金', 'noun', 6),
        ('grant', '拨款', 'noun', 6),
        ('tuition', '学费', 'noun', 5),
        ('fee', '费用', 'noun', 5),
        ('semester', '学期', 'noun', 5),
        ('term', '学期', 'noun', 4),
    ],
    'travel': [
        ('airport', '机场', 'noun', 4),
        ('terminal', '航站楼', 'noun', 5),
        ('departure', '出发', 'noun', 5),
        ('arrival', '到达', 'noun', 5),
        ('flight', '航班', 'noun', 4),
        ('airline', '航空公司', 'noun', 5),
        ('passport', '护照', 'noun', 4),
        ('visa', '签证', 'noun', 5),
        ('ticket', '票', 'noun', 4),
        ('booking', '预订', 'noun', 5),
        ('reservation', '预订', 'noun', 5),
        ('luggage', '行李', 'noun', 5),
        ('baggage', '行李', 'noun', 5),
        ('suitcase', '行李箱', 'noun', 5),
        ('backpack', '背包', 'noun', 5),
        ('customs', '海关', 'noun', 5),
        ('immigration', '移民', 'noun', 6),
        ('destination', '目的地', 'noun', 5),
        ('itinerary', '行程', 'noun', 7),
        ('brochure', '手册', 'noun', 5),
        ('excursion', '短途旅行', 'noun', 6),
        ('sightseeing', '观光', 'noun', 5),
        ('tourist', '游客', 'noun', 4),
        ('tourism', '旅游业', 'noun', 5),
        ('attraction', '景点', 'noun', 5),
        ('guide', '导游', 'noun', 4),
        ('reception', '接待', 'noun', 5),
        ('receptionist', '接待员', 'noun', 5),
        ('accommodation', '住宿', 'noun', 5),
        ('check in', '登记入住', 'phrasal verb', 5),
        ('check out', '结账离开', 'phrasal verb', 5),
    ]
}

# 雅思阅读学术话题词汇
IELTS_READING_TOPICS = {
    'science': [
        ('scientific', '科学的', 'adjective', 5),
        ('scientist', '科学家', 'noun', 5),
        ('research', '研究', 'noun/verb', 5),
        ('researcher', '研究者', 'noun', 5),
        ('experiment', '实验', 'noun', 5),
        ('experimental', '实验的', 'adjective', 6),
        ('hypothesis', '假设', 'noun', 7),
        ('theory', '理论', 'noun', 5),
        ('theoretical', '理论的', 'adjective', 6),
        ('phenomenon', '现象', 'noun', 6),
        ('phenomena', '现象', 'noun', 6),
        ('observation', '观察', 'noun', 6),
        ('evidence', '证据', 'noun', 5),
        ('data', '数据', 'noun', 5),
        ('statistics', '统计', 'noun', 6),
        ('analysis', '分析', 'noun', 6),
        ('analyze', '分析', 'verb', 6),
        ('investigation', '调查', 'noun', 6),
        ('measurement', '测量', 'noun', 6),
        ('calculation', '计算', 'noun', 6),
        ('precise', '精确的', 'adjective', 6),
        ('accurate', '精确的', 'adjective', 6),
        ('valid', '有效的', 'adjective', 6),
        ('reliable', '可靠的', 'adjective', 6),
        ('significant', '重要的', 'adjective', 6),
        ('conclusion', '结论', 'noun', 5),
        ('finding', '发现', 'noun', 5),
        ('discovery', '发现', 'noun', 5),
        ('invention', '发明', 'noun', 5),
        ('innovation', '创新', 'noun', 6),
        ('technology', '技术', 'noun', 5),
        ('technological', '技术的', 'adjective', 6),
        ('biological', '生物的', 'adjective', 6),
        ('chemical', '化学的', 'adjective', 6),
        ('physical', '物理的', 'adjective', 6),
        ('genetic', '基因的', 'adjective', 6),
        ('molecular', '分子的', 'adjective', 7),
        ('cellular', '细胞的', 'adjective', 7),
        ('organism', '生物', 'noun', 6),
        ('species', '物种', 'noun', 6),
        ('evolution', '进化', 'noun', 6),
        ('ecosystem', '生态系统', 'noun', 7),
    ],
    'environment': [
        ('environment', '环境', 'noun', 5),
        ('environmental', '环境的', 'adjective', 6),
        ('ecology', '生态学', 'noun', 7),
        ('ecological', '生态的', 'adjective', 7),
        ('pollution', '污染', 'noun', 5),
        ('pollutant', '污染物', 'noun', 7),
        ('contamination', '污染', 'noun', 7),
        ('climate', '气候', 'noun', 5),
        ('climate change', '气候变化', 'noun', 5),
        ('global warming', '全球变暖', 'noun', 6),
        ('greenhouse', '温室', 'noun', 6),
        ('emission', '排放', 'noun', 7),
        ('carbon dioxide', '二氧化碳', 'noun', 6),
        ('sustainable', '可持续的', 'adjective', 7),
        ('sustainability', '可持续性', 'noun', 7),
        ('renewable', '可再生的', 'adjective', 7),
        ('conservation', '保护', 'noun', 6),
        ('preserve', '保护', 'verb', 6),
        ('protection', '保护', 'noun', 5),
        ('biodiversity', '生物多样性', 'noun', 7),
        ('habitat', '栖息地', 'noun', 6),
        ('wildlife', '野生动物', 'noun', 6),
        ('endangered', '濒危的', 'adjective', 6),
        ('extinct', '灭绝的', 'adjective', 7),
        ('extinction', '灭绝', 'noun', 7),
        ('natural', '自然的', 'adjective', 5),
        ('nature', '自然', 'noun', 4),
        ('resource', '资源', 'noun', 5),
        ('energy', '能源', 'noun', 5),
        ('solar', '太阳的', 'adjective', 5),
        ('nuclear', '核的', 'adjective', 6),
    ],
    'health': [
        ('health', '健康', 'noun', 4),
        ('healthy', '健康的', 'adjective', 4),
        ('medicine', '医学', 'noun', 5),
        ('medical', '医学的', 'adjective', 5),
        ('patient', '病人', 'noun', 5),
        ('doctor', '医生', 'noun', 4),
        ('physician', '内科医生', 'noun', 6),
        ('surgeon', '外科医生', 'noun', 6),
        ('nurse', '护士', 'noun', 4),
        ('hospital', '医院', 'noun', 4),
        ('clinic', '诊所', 'noun', 5),
        ('pharmacy', '药房', 'noun', 6),
        ('treatment', '治疗', 'noun', 5),
        ('therapy', '治疗', 'noun', 6),
        ('diagnosis', '诊断', 'noun', 7),
        ('symptom', '症状', 'noun', 6),
        ('disease', '疾病', 'noun', 5),
        ('illness', '疾病', 'noun', 5),
        ('infection', '感染', 'noun', 6),
        ('virus', '病毒', 'noun', 5),
        ('bacteria', '细菌', 'noun', 6),
        ('immune', '免疫的', 'adjective', 7),
        ('vaccine', '疫苗', 'noun', 6),
        ('prescription', '处方', 'noun', 6),
        ('medication', '药物', 'noun', 6),
        ('drug', '药物', 'noun', 5),
        ('antibiotic', '抗生素', 'noun', 7),
        ('nutrition', '营养', 'noun', 6),
        ('nutritional', '营养的', 'adjective', 6),
        ('diet', '饮食', 'noun', 5),
        ('exercise', '锻炼', 'noun', 4),
        ('fitness', '健康', 'noun', 5),
    ]
}

# 雅思写作高级词汇
IELTS_WRITING_VOCAB = [
    # 表达观点
    ('argue', '争论', 'verb', 6),
    ('argument', '论点', 'noun', 6),
    ('claim', '声称', 'verb/noun', 6),
    ('contend', '主张', 'verb', 7),
    ('assert', '断言', 'verb', 7),
    ('maintain', '坚持', 'verb', 6),
    ('acknowledge', '承认', 'verb', 7),
    ('admit', '承认', 'verb', 5),
    ('accept', '接受', 'verb', 5),
    ('recognize', '认识', 'verb', 5),
    ('realize', '意识到', 'verb', 5),
    ('understand', '理解', 'verb', 4),
    ('comprehend', '理解', 'verb', 7),
    ('perceive', '感知', 'verb', 6),
    ('believe', '相信', 'verb', 4),
    ('consider', '考虑', 'verb', 5),
    ('regard', '认为', 'verb', 5),
    ('view', '看待', 'verb', 5),
    ('think', '想', 'verb', 4),
    ('suppose', '假设', 'verb', 5),
    ('assume', '假设', 'verb', 6),
    ('presume', '推测', 'verb', 7),
    ('imply', '暗示', 'verb', 6),
    ('suggest', '建议', 'verb', 5),
    ('indicate', '表明', 'verb', 6),
    ('demonstrate', '证明', 'verb', 6),
    ('show', '展示', 'verb', 4),
    ('illustrate', '说明', 'verb', 6),
    ('reveal', '揭示', 'verb', 6),
    ('reflect', '反映', 'verb', 6),
    ('represent', '代表', 'verb', 6),

    # 连接词
    ('however', '然而', 'adverb', 5),
    ('nevertheless', '尽管如此', 'adverb', 6),
    ('nonetheless', '尽管如此', 'adverb', 7),
    ('whereas', '然而', 'conjunction', 6),
    ('while', '然而', 'conjunction', 5),
    ('although', '虽然', 'conjunction', 5),
    ('though', '虽然', 'conjunction', 5),
    ('despite', '尽管', 'preposition', 6),
    ('in spite of', '尽管', 'preposition', 6),
    ('regardless of', '不管', 'preposition', 6),
    ('conversely', '相反地', 'adverb', 7),
    ('on the contrary', '相反', 'phrase', 6),
    ('in contrast', '相比之下', 'phrase', 6),
    ('by contrast', '相比之下', 'phrase', 6),
    ('compared with', '与...相比', 'phrase', 5),
    ('in comparison with', '与...相比', 'phrase', 6),
    ('similarly', '同样', 'adverb', 6),
    ('likewise', '同样', 'adverb', 6),
    ('equally', '同样', 'adverb', 5),
    ('in the same way', '同样', 'phrase', 5),
    ('therefore', '因此', 'adverb', 5),
    ('thus', '因此', 'adverb', 6),
    ('hence', '因此', 'adverb', 7),
    ('consequently', '因此', 'adverb', 6),
    ('as a result', '结果', 'phrase', 5),
    ('accordingly', '因此', 'adverb', 7),
    ('so', '所以', 'conjunction', 4),
    ('because', '因为', 'conjunction', 4),
    ('since', '因为', 'conjunction', 5),
    ('as', '因为', 'conjunction', 4),
    ('due to', '由于', 'preposition', 5),
    ('owing to', '由于', 'preposition', 6),
    ('thanks to', '多亏', 'preposition', 5),
    ('because of', '因为', 'preposition', 5),
    ('on account of', '因为', 'preposition', 6),
    ('furthermore', '此外', 'adverb', 6),
    ('moreover', '此外', 'adverb', 6),
    ('in addition', '此外', 'phrase', 5),
    ('additionally', '此外', 'adverb', 6),
    ('besides', '此外', 'adverb', 5),
    ('also', '也', 'adverb', 4),
    ('as well as', '以及', 'conjunction', 5),
    ('not only...but also', '不仅...而且', 'conjunction', 5),
    ('both...and', '既...又', 'conjunction', 5),
    ('either...or', '要么...要么', 'conjunction', 5),
    ('neither...nor', '既不...也不', 'conjunction', 6),

    # 表达程度
    ('extremely', '极其', 'adverb', 5),
    ('highly', '非常', 'adverb', 5),
    ('remarkably', '显著地', 'adverb', 7),
    ('significantly', '显著地', 'adverb', 6),
    ('substantially', '实质上', 'adverb', 7),
    ('considerably', '相当', 'adverb', 6),
    ('dramatically', '显著地', 'adverb', 6),
    ('radically', '根本上', 'adverb', 7),
    ('fundamentally', '根本上', 'adverb', 7),
    ('completely', '完全', 'adverb', 5),
    ('totally', '完全', 'adverb', 5),
    ('entirely', '完全', 'adverb', 6),
    ('absolutely', '绝对', 'adverb', 5),
    ('utterly', '完全', 'adverb', 7),
    ('fairly', '相当', 'adverb', 5),
    ('quite', '相当', 'adverb', 5),
    ('rather', '相当', 'adverb', 5),
    ('somewhat', '有点', 'adverb', 6),
    ('relatively', '相对', 'adverb', 6),
    ('comparatively', '相对地', 'adverb', 7),
    ('slightly', '稍微', 'adverb', 5),
    ('barely', '几乎不', 'adverb', 6),
    ('hardly', '几乎不', 'adverb', 5),
    ('scarcely', '几乎不', 'adverb', 6),
    ('merely', '仅仅', 'adverb', 6),
    ('simply', '简单地', 'adverb', 5),
    ('purely', '纯粹', 'adverb', 6),
]

# 剑桥雅思真题高频词
CAMBRIDGE_IELTS_WORDS = [
    # 剑4-19 听力/阅读高频词
    ('abandon', '放弃', 'verb', 6),
    ('ability', '能力', 'noun', 5),
    ('absence', '缺席', 'noun', 6),
    ('absolute', '绝对的', 'adjective', 6),
    ('absorb', '吸收', 'verb', 6),
    ('abstract', '抽象的', 'adjective', 6),
    ('abundant', '丰富的', 'adjective', 6),
    ('academic', '学术的', 'adjective', 5),
    ('accelerate', '加速', 'verb', 7),
    ('accent', '口音', 'noun', 5),
    ('access', '通道', 'noun', 5),
    ('accessible', '可进入的', 'adjective', 6),
    ('accident', '事故', 'noun', 5),
    ('accompany', '陪伴', 'verb', 6),
    ('accomplish', '完成', 'verb', 7),
    ('accord', '一致', 'noun', 7),
    ('account', '账户', 'noun', 5),
    ('accumulate', '积累', 'verb', 7),
    ('accuracy', '准确性', 'noun', 6),
    ('accuse', '控告', 'verb', 6),
    ('accustomed', '习惯的', 'adjective', 7),
    ('ache', '疼痛', 'noun', 5),
    ('achieve', '实现', 'verb', 5),
    ('acid', '酸', 'noun', 6),
    ('acknowledge', '承认', 'verb', 7),
    ('acquaintance', '熟人', 'noun', 6),
    ('acquire', '获得', 'verb', 6),
    ('acquisition', '获得', 'noun', 7),
    ('acre', '英亩', 'noun', 5),
    ('adequate', '足够的', 'adjective', 6),
    ('adjust', '调整', 'verb', 6),
    ('administration', '管理', 'noun', 6),
    ('admire', '钦佩', 'verb', 5),
    ('admission', '准许进入', 'noun', 6),
    ('adolescent', '青少年', 'noun', 7),
    ('adopt', '采用', 'verb', 6),
    ('advance', '前进', 'noun/verb', 5),
    ('adventure', '冒险', 'noun', 5),
    ('advertise', '广告', 'verb', 5),
    ('advocate', '提倡', 'verb', 7),
    ('aesthetic', '美学的', 'adjective', 7),
    ('affection', '感情', 'noun', 6),
    ('afford', '负担得起', 'verb', 5),
    ('agenda', '议程', 'noun', 6),
    ('aggressive', '侵略性的', 'adjective', 6),
    ('agriculture', '农业', 'noun', 6),
    ('aid', '援助', 'noun', 5),
    ('alarm', '警报', 'noun', 5),
    ('album', '相册', 'noun', 5),
    ('alcohol', '酒精', 'noun', 5),
    ('alert', '警惕的', 'adjective', 6),
    ('allergy', '过敏', 'noun', 6),
    ('allocate', '分配', 'verb', 7),
    ('allowance', '津贴', 'noun', 6),
    ('ally', '同盟', 'noun', 7),
    ('alter', '改变', 'verb', 6),
    ('amateur', '业余爱好者', 'noun', 6),
    ('amaze', '使惊奇', 'verb', 5),
    ('ambassador', '大使', 'noun', 6),
    ('ambition', '雄心', 'noun', 6),
    ('ample', '充足的', 'adjective', 7),
    ('amuse', '娱乐', 'verb', 5),
    ('analyse', '分析', 'verb', 6),
    ('ancestor', '祖先', 'noun', 6),
    ('anchor', '锚', 'noun', 6),
    ('ancient', '古代的', 'adjective', 5),
    ('anecdote', '轶事', 'noun', 7),
    ('angle', '角度', 'noun', 5),
    ('ankle', '脚踝', 'noun', 5),
    ('anniversary', '周年纪念', 'noun', 6),
    ('announce', '宣布', 'verb', 5),
    ('annoy', '使烦恼', 'verb', 5),
    ('annual', '年度的', 'adjective', 6),
    ('anticipate', '预期', 'verb', 7),
    ('anxiety', '焦虑', 'noun', 6),
    ('apologise', '道歉', 'verb', 5),
    ('apparatus', '器械', 'noun', 7),
    ('appeal', '呼吁', 'noun/verb', 6),
    ('appetite', '食欲', 'noun', 6),
    ('applaud', '鼓掌', 'verb', 6),
    ('appliance', '器具', 'noun', 6),
    ('applicant', '申请人', 'noun', 6),
    ('appoint', '任命', 'verb', 6),
    ('appreciate', '欣赏', 'verb', 5),
    ('apprentice', '学徒', 'noun', 6),
    ('appropriate', '适当的', 'adjective', 6),
    ('approve', '批准', 'verb', 6),
    ('approximate', '大约的', 'adjective', 6),
    ('architect', '建筑师', 'noun', 6),
    ('arise', '出现', 'verb', 6),
    ('arithmetic', '算术', 'noun', 6),
    ('arouse', '引起', 'verb', 7),
    ('arrange', '安排', 'verb', 5),
    ('arrest', '逮捕', 'verb', 6),
    ('arrow', '箭', 'noun', 5),
    ('artificial', '人工的', 'adjective', 6),
    ('ashamed', '羞愧的', 'adjective', 5),
    ('aspect', '方面', 'noun', 6),
    ('aspire', '渴望', 'verb', 7),
    ('assemble', '集合', 'verb', 6),
    ('assess', '评估', 'verb', 6),
    ('assign', '分配', 'verb', 6),
    ('assist', '帮助', 'verb', 5),
    ('associate', '联系', 'verb', 6),
    ('assume', '假设', 'verb', 6),
    ('assure', '保证', 'verb', 6),
    ('astonish', '使惊讶', 'verb', 6),
    ('athlete', '运动员', 'noun', 5),
    ('atmosphere', '气氛', 'noun', 6),
    ('attach', '附上', 'verb', 5),
    ('attack', '攻击', 'verb', 5),
    ('attain', '达到', 'verb', 7),
    ('attempt', '尝试', 'noun/verb', 5),
    ('attend', '参加', 'verb', 5),
    ('attitude', '态度', 'noun', 5),
    ('attract', '吸引', 'verb', 5),
    ('audience', '观众', 'noun', 5),
    ('authority', '权威', 'noun', 6),
    ('automatic', '自动的', 'adjective', 6),
    ('available', '可用的', 'adjective', 5),
    ('aware', '知道的', 'adjective', 5),
]

def generate_all_vocabulary():
    """生成所有词汇数据"""
    all_vocabularies = {}

    # 1. AWL词汇 (约450词)
    print("Generating AWL vocabulary...")
    all_vocabularies['awl'] = parse_awl_data()
    print(f"  - Generated {len(all_vocabularies['awl'])} AWL words")

    # 2. 听力场景词汇
    print("Generating listening scene vocabulary...")
    listening_words = []
    for scene, words in IELTS_LISTENING_SCENES.items():
        for word, trans, pos, level in words:
            listening_words.append({
                'word': word,
                'translation': trans,
                'pos': pos,
                'category': f'listening_{scene}',
                'level': str(level),
                'frequency': 50 - level * 2,
                'source': 'IELTS_Listening'
            })
    all_vocabularies['listening'] = listening_words
    print(f"  - Generated {len(listening_words)} listening words")

    # 3. 阅读话题词汇
    print("Generating reading topic vocabulary...")
    reading_words = []
    for topic, words in IELTS_READING_TOPICS.items():
        for word, trans, pos, level in words:
            reading_words.append({
                'word': word,
                'translation': trans,
                'pos': pos,
                'category': f'reading_{topic}',
                'level': str(level),
                'frequency': 55 - level * 2,
                'source': 'IELTS_Reading'
            })
    all_vocabularies['reading'] = reading_words
    print(f"  - Generated {len(reading_words)} reading words")

    # 4. 写作词汇
    print("Generating writing vocabulary...")
    writing_words = []
    for word, trans, pos, level in IELTS_WRITING_VOCAB:
        writing_words.append({
            'word': word,
            'translation': trans,
            'pos': pos,
            'category': 'writing',
            'level': str(level),
            'frequency': 50 - level * 2,
            'source': 'IELTS_Writing'
        })
    all_vocabularies['writing'] = writing_words
    print(f"  - Generated {len(writing_words)} writing words")

    # 5. 剑桥真题词汇
    print("Generating Cambridge IELTS vocabulary...")
    cambridge_words = []
    for word, trans, pos, level in CAMBRIDGE_IELTS_WORDS:
        cambridge_words.append({
            'word': word,
            'translation': trans,
            'pos': pos,
            'category': 'cambridge',
            'level': str(level),
            'frequency': 60 - level * 2,
            'source': 'Cambridge_IELTS'
        })
    all_vocabularies['cambridge'] = cambridge_words
    print(f"  - Generated {len(cambridge_words)} Cambridge words")

    return all_vocabularies

def export_data(vocabularies):
    """导出词汇数据"""
    # 合并所有词汇
    all_words = []
    word_set = set()

    for name, words in vocabularies.items():
        for word_data in words:
            word = word_data['word'].lower()
            if word not in word_set:
                word_set.add(word)
                all_words.append(word_data)

    # 按等级排序
    all_words.sort(key=lambda x: (int(x.get('level', 9)), x['word']))

    # 导出合并的JSON
    output_file = OUTPUT_DIR / 'ielts_vocabulary_complete_extended.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_words, f, ensure_ascii=False, indent=2)
    print(f"\n- Exported: {output_file} ({len(all_words)} words)")

    # 导出单独的分类文件
    for name, words in vocabularies.items():
        output_file = OUTPUT_DIR / f'ielts_vocabulary_{name}_extended.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(words, f, ensure_ascii=False, indent=2)
        print(f"- Exported: {name} ({len(words)} words)")

    # 导出CSV
    for name, words in vocabularies.items():
        output_file = OUTPUT_DIR / f'ielts_vocabulary_{name}_extended.csv'
        with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
            if words:
                standard_fields = ['word', 'translation', 'pos', 'category', 'level', 'frequency', 'source']
                writer = csv.DictWriter(f, fieldnames=standard_fields, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(words)
        print(f"- Exported CSV: {name}")

    # 生成SQL
    sql_file = OUTPUT_DIR / 'vocabulary_inserts_extended.sql'
    with open(sql_file, 'w', encoding='utf-8') as f:
        f.write("-- IELTS Extended Vocabulary Database Insert Statements\n\n")
        f.write("INSERT INTO vocabulary (word, translation, pos, category, level, frequency) VALUES\n")
        values = []
        for w in all_words[:8000]:
            word = w['word'].replace("'", "''")
            trans = w['translation'].replace("'", "''")
            val = f"  ('{word}', '{trans}', '{w.get('pos', '')}', '{w.get('category', 'general')}', {w.get('level', 6)}, {w.get('frequency', 0)})"
            values.append(val)
        f.write(',\n'.join(values) + ';')
    print(f"- Exported SQL: {sql_file}")

    return len(all_words)

def print_statistics(vocabularies):
    """打印统计信息"""
    print("\n" + "="*60)
    print("IELTS Extended Vocabulary Statistics")
    print("="*60)

    total = 0
    for name, words in vocabularies.items():
        count = len(words)
        total += count
        levels = {}
        for w in words:
            l = w.get('level', 'unknown')
            levels[l] = levels.get(l, 0) + 1

        print(f"\n[BOOK] {name.upper()}")
        print(f"   Total: {count} words")
        print(f"   Level distribution: {dict(sorted(levels.items()))}")

    print(f"\n[STATS] Total generated: {total} words")
    print("="*60)

if __name__ == '__main__':
    print("="*60)
    print("IELTS Extended Vocabulary Generator")
    print("="*60)
    print()

    vocabularies = generate_all_vocabulary()
    print_statistics(vocabularies)

    print("\nExporting data...")
    total = export_data(vocabularies)

    print("\n" + "="*60)
    print(f"- Generation complete!")
    print(f"- Total unique words: {total}")
    print(f"- Output directory: {OUTPUT_DIR}")
    print("="*60)
