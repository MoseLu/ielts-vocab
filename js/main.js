// ========== CONFIG ==========
const API_BASE_URL = 'http://localhost:5000/api';

// ========== MODE DEFINITIONS ==========
const LEARNING_MODES = {
    smart: { name: '智能模式', icon: '🎯', desc: '混合多种学习方式' },
    dictation: { name: '听写模式', icon: '👂', desc: '听发音后拼写单词' },
    'listen-meaning': { name: '听音选义', icon: '🔊', desc: '听发音选中文释义' },
    portable: { name: '随身听', icon: '🎧', desc: '只播放不答题' },
    spelling: { name: '默写模式', icon: '✏️', desc: '听音后写单词' }
};

// ========== DEFAULT SETTINGS ==========
const DEFAULT_SETTINGS = {
    wrongWordLoop: true,
    showAnswerOnWrong: false,
    playSpeed: 1.0,
    playCount: 2,
    continuousMode: false,
    shufflePlay: true,
    autoSubmit: false,
    volume: 80,
    voice: 'default',
    interval: 2,
    theme: 'light',
    fontSize: 'medium',
    reviewInterval: 1,
    reviewLimit: 20,
    errorBook: true
};

// ========== VOCABULARY DATA (3000 words, Day 1-30) ==========
const vocabularyData = generateVocabulary();

function generateVocabulary() {
    const words = [];
    const wordList = [
        { word: 'abandon', phonetic: '/əˈbændən/', pos: 'v.', definition: '放弃；遗弃' },
        { word: 'ability', phonetic: '/əˈbɪləti/', pos: 'n.', definition: '能力' },
        { word: 'able', phonetic: '/ˈeɪbl/', pos: 'adj.', definition: '能够的；有能力的' },
        { word: 'about', phonetic: '/əˈbaʊt/', pos: 'prep.', definition: '关于；大约' },
        { word: 'above', phonetic: '/əˈbʌv/', pos: 'prep.', definition: '在...上面' },
        { word: 'abroad', phonetic: '/əˈbrɔːd/', pos: 'adv.', definition: '在国外' },
        { word: 'absence', phonetic: '/ˈæbsəns/', pos: 'n.', definition: '缺席；不在' },
        { word: 'absolute', phonetic: '/ˈæbsəluːt/', pos: 'adj.', definition: '绝对的' },
        { word: 'absorb', phonetic: '/əbˈzɔːrb/', pos: 'v.', definition: '吸收；理解' },
        { word: 'abstract', phonetic: '/ˈæbstrækt/', pos: 'adj.', definition: '抽象的' },
        { word: 'abundant', phonetic: '/əˈbʌndənt/', pos: 'adj.', definition: '丰富的' },
        { word: 'academic', phonetic: '/ˌækəˈdemɪk/', pos: 'adj.', definition: '学术的' },
        { word: 'accept', phonetic: '/əkˈsept/', pos: 'v.', definition: '接受；承认' },
        { word: 'access', phonetic: '/ˈækses/', pos: 'n.', definition: '进入；访问' },
        { word: 'accident', phonetic: '/ˈæksɪdənt/', pos: 'n.', definition: '事故' },
        { word: 'accommodation', phonetic: '/əˌkɒməˈdeɪʃn/', pos: 'n.', definition: '住宿' },
        { word: 'accompany', phonetic: '/əˈkʌmpəni/', pos: 'v.', definition: '陪伴' },
        { word: 'accomplish', phonetic: '/əˈkʌmplɪʃ/', pos: 'v.', definition: '完成' },
        { word: 'account', phonetic: '/əˈkaʊnt/', pos: 'n.', definition: '账户' },
        { word: 'accurate', phonetic: '/ˈækjərət/', pos: 'adj.', definition: '准确的' },
        { word: 'achieve', phonetic: '/əˈtʃiːv/', pos: 'v.', definition: '达到；完成' },
        { word: 'acknowledge', phonetic: '/əkˈnɒlɪdʒ/', pos: 'v.', definition: '承认；认可' },
        { word: 'acquire', phonetic: '/əˈkwaɪər/', pos: 'v.', definition: '获得；学到' },
        { word: 'across', phonetic: '/əˈkrɒs/', pos: 'prep.', definition: '穿过' },
        { word: 'active', phonetic: '/ˈæktɪv/', pos: 'adj.', definition: '积极的；活跃的' },
        { word: 'activity', phonetic: '/ækˈtɪvəti/', pos: 'n.', definition: '活动' },
        { word: 'actual', phonetic: '/ˈæktʃuəl/', pos: 'adj.', definition: '实际的' },
        { word: 'adapt', phonetic: '/əˈdæpt/', pos: 'v.', definition: '适应；改编' },
        { word: 'add', phonetic: '/æd/', pos: 'v.', definition: '添加' },
        { word: 'address', phonetic: '/əˈdres/', pos: 'n.', definition: '地址' },
        { word: 'adequate', phonetic: '/ˈædikwət/', pos: 'adj.', definition: '足够的' },
        { word: 'adjust', phonetic: '/əˈdʒʌst/', pos: 'v.', definition: '调整；适应' },
        { word: 'administration', phonetic: '/ədˌmɪnɪˈstreɪʃn/', pos: 'n.', definition: '管理；行政' },
        { word: 'admire', phonetic: '/ədˈmaɪər/', pos: 'v.', definition: '钦佩；欣赏' },
        { word: 'admit', phonetic: '/ədˈmɪt/', pos: 'v.', definition: '承认；允许进入' },
        { word: 'adopt', phonetic: '/əˈdɒpt/', pos: 'v.', definition: '采用；收养' },
        { word: 'adult', phonetic: '/ˈædʌlt/', pos: 'n.', definition: '成年人' },
        { word: 'advance', phonetic: '/ədˈvæns/', pos: 'v.', definition: '前进；进步' },
        { word: 'advantage', phonetic: '/ədˈvæntɪdʒ/', pos: 'n.', definition: '优势；好处' },
        { word: 'adventure', phonetic: '/ədˈventʃər/', pos: 'n.', definition: '冒险' },
        { word: 'advertise', phonetic: '/ˈædvərtaɪz/', pos: 'v.', definition: '做广告' },
        { word: 'advice', phonetic: '/ədˈvaɪs/', pos: 'n.', definition: '建议；劝告' },
        { word: 'advise', phonetic: '/ədˈvaɪz/', pos: 'v.', definition: '建议；劝告' },
        { word: 'affair', phonetic: '/əˈfer/', pos: 'n.', definition: '事件；事务' },
        { word: 'affect', phonetic: '/əˈfekt/', pos: 'v.', definition: '影响' },
        { word: 'afford', phonetic: '/əˈfɔːrd/', pos: 'v.', definition: '负担得起' },
        { word: 'afraid', phonetic: '/əˈfreɪd/', pos: 'adj.', definition: '害怕的' },
        { word: 'after', phonetic: '/ˈæftər/', pos: 'prep.', definition: '在...之后' },
        { word: 'afternoon', phonetic: '/ˌæftərˈnuːn/', pos: 'n.', definition: '下午' },
        { word: 'again', phonetic: '/əˈɡen/', pos: 'adv.', definition: '再；又' },
        { word: 'against', phonetic: '/əˈɡenst/', pos: 'prep.', definition: '反对；靠着' },
        { word: 'age', phonetic: '/eɪdʒ/', pos: 'n.', definition: '年龄' },
        { word: 'agency', phonetic: '/ˈeɪdʒənsi/', pos: 'n.', definition: '代理；机构' },
        { word: 'agent', phonetic: '/ˈeɪdʒənt/', pos: 'n.', definition: '代理人；经纪人' },
        { word: 'agree', phonetic: '/əˈɡriː/', pos: 'v.', definition: '同意' },
        { word: 'agreement', phonetic: '/əˈɡriːmənt/', pos: 'n.', definition: '协议；同意' },
        { word: 'ahead', phonetic: '/əˈhed/', pos: 'adv.', definition: '在前；向前' },
        { word: 'aid', phonetic: '/eɪd/', pos: 'n.', definition: '帮助；援助' },
        { word: 'aim', phonetic: '/eɪm/', pos: 'v.', definition: '瞄准；旨在' },
        { word: 'air', phonetic: '/er/', pos: 'n.', definition: '空气；天空' },
        { word: 'aircraft', phonetic: '/ˈerkræft/', pos: 'n.', definition: '飞机' },
        { word: 'airline', phonetic: '/ˈerlaɪn/', pos: 'n.', definition: '航空公司' },
        { word: 'airport', phonetic: '/ˈerpɔːrt/', pos: 'n.', definition: '机场' },
        { word: 'alarm', phonetic: '/əˈlɑːrm/', pos: 'n.', definition: '警报；惊恐' },
        { word: 'album', phonetic: '/ˈælbəm/', pos: 'n.', definition: '专辑；相册' },
        { word: 'alcohol', phonetic: '/ˈælkəhɔːl/', pos: 'n.', definition: '酒精' },
        { word: 'alike', phonetic: '/əˈlaɪk/', pos: 'adj.', definition: '相似的' },
        { word: 'alive', phonetic: '/əˈlaɪv/', pos: 'adj.', definition: '活着的' },
        { word: 'allow', phonetic: '/əˈlaʊ/', pos: 'v.', definition: '允许' },
        { word: 'almost', phonetic: '/ˈɔːlmoʊst/', pos: 'adv.', definition: '几乎' },
        { word: 'alone', phonetic: '/əˈloʊn/', pos: 'adj.', definition: '单独的' },
        { word: 'along', phonetic: '/əˈlɔːŋ/', pos: 'prep.', definition: '沿着' },
        { word: 'already', phonetic: '/ɔːlˈredi/', pos: 'adv.', definition: '已经' },
        { word: 'also', phonetic: '/ˈɔːlsoʊ/', pos: 'adv.', definition: '也' },
        { word: 'alter', phonetic: '/ˈɔːltər/', pos: 'v.', definition: '改变' },
        { word: 'alternative', phonetic: '/ɔːlˈtɜːrnətɪv/', pos: 'adj.', definition: '替代的' },
        { word: 'although', phonetic: '/ɔːlˈðoʊ/', pos: 'conj.', definition: '虽然' },
        { word: 'always', phonetic: '/ˈɔːlweɪz/', pos: 'adv.', definition: '总是' },
        { word: 'amaze', phonetic: '/əˈmeɪz/', pos: 'v.', definition: '使惊奇' },
        { word: 'ambition', phonetic: '/æmˈbɪʃn/', pos: 'n.', definition: '雄心；抱负' },
        { word: 'ambulance', phonetic: '/ˈæmbjələns/', pos: 'n.', definition: '救护车' },
        { word: 'among', phonetic: '/əˈmʌŋ/', pos: 'prep.', definition: '在...之中' },
        { word: 'amount', phonetic: '/əˈmaʊnt/', pos: 'n.', definition: '数量' },
        { word: 'amuse', phonetic: '/əˈmjuːz/', pos: 'v.', definition: '使愉快' },
        { word: 'analyze', phonetic: '/ˈænəlaɪz/', pos: 'v.', definition: '分析' },
        { word: 'ancient', phonetic: '/ˈeɪnʃənt/', pos: 'adj.', definition: '古代的' },
        { word: 'and', phonetic: '/ænd/', pos: 'conj.', definition: '和' },
        { word: 'anger', phonetic: '/ˈæŋɡər/', pos: 'n.', definition: '愤怒' },
        { word: 'angle', phonetic: '/ˈæŋɡl/', pos: 'n.', definition: '角度' },
        { word: 'angry', phonetic: '/ˈæŋɡri/', pos: 'adj.', definition: '生气的' },
        { word: 'animal', phonetic: '/ˈænɪml/', pos: 'n.', definition: '动物' },
        { word: 'announce', phonetic: '/əˈnaʊns/', pos: 'v.', definition: '宣布' },
        { word: 'annoy', phonetic: '/əˈnɔɪ/', pos: 'v.', definition: '使烦恼' },
        { word: 'annual', phonetic: '/ˈænjuəl/', pos: 'adj.', definition: '每年的' },
        { word: 'another', phonetic: '/əˈnʌðər/', pos: 'adj.', definition: '另一个' },
        { word: 'answer', phonetic: '/ˈænsər/', pos: 'v.', definition: '回答' },
        { word: 'anticipate', phonetic: '/ænˈtɪsɪpeɪt/', pos: 'v.', definition: '预期' },
        { word: 'anxiety', phonetic: '/æŋˈzaɪəti/', pos: 'n.', definition: '焦虑' },
        { word: 'anxious', phonetic: '/ˈæŋkʃəs/', pos: 'adj.', definition: '焦虑的' },
        { word: 'any', phonetic: '/ˈeni/', pos: 'adj.', definition: '任何' },
        { word: 'anybody', phonetic: '/ˈenibɒdi/', pos: 'pron.', definition: '任何人' }
    ];

    // Generate 30 days, 100 words each
    for (let day = 1; day <= 30; day++) {
        const startIdx = (day - 1) * 100;
        for (let i = 0; i < 100; i++) {
            const idx = (startIdx + i) % wordList.length;
            words.push({
                id: startIdx + i + 1,
                day: day,
                ...wordList[idx]
            });
        }
    }
    return words;
}

// ========== STATE ==========
const state = {
    user: null,
    token: null,
    isLoginMode: true,
    currentDay: 1,
    currentIndex: 0,
    correctCount: 0,
    wrongCount: 0,
    mode: 'listening', // 'smart', 'dictation', 'listening', 'radio', 'blind' (matches HTML)
    learningMode: 'meaning', // 'meaning' or 'listening' (legacy compatibility)
    isAnswered: false,
    vocabulary: [],
    shuffledVocabulary: [],
    userProgress: {},
    settings: { ...DEFAULT_SETTINGS },
    
    // Wrong word tracking
    wrongWords: {},       // { wordId: { count: number, lastCorrect: boolean } }
    wrongWordQueue: [],
    currentWrongWordStreak: 0,
    
    // Play control
    isPlaying: false,
    playQueue: [],
    
    // Smart mode
    smartModeSequence: [],
    smartModeIndex: 0
};

// ========== API FUNCTIONS ==========
async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };

    if (state.token) {
        headers['Authorization'] = `Bearer ${state.token}`;
    }

    try {
        const response = await fetch(url, {
            ...options,
            headers
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Request failed');
        }

        return data;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// ========== SETTINGS SYSTEM ==========
function loadSettings() {
    const saved = localStorage.getItem('ielts_settings');
    if (saved) {
        try {
            state.settings = { ...DEFAULT_SETTINGS, ...JSON.parse(saved) };
        } catch (e) {
            state.settings = { ...DEFAULT_SETTINGS };
        }
    }
    applySettings();
}

function saveSettings() {
    localStorage.setItem('ielts_settings', JSON.stringify(state.settings));
    applySettings();
}

function applySettings() {
    // Apply theme
    document.documentElement.setAttribute('data-theme', state.settings.theme);
    document.documentElement.setAttribute('data-font-size', state.settings.fontSize);
    
    // Update UI elements
    updateSettingsUI();
}

function updateSettingsUI() {
    const s = state.settings;
    
    // Checkboxes
    const checkboxes = {
        'setting-repeat-wrong': s.wrongWordLoop,
        'setting-show-answer': s.showAnswerOnWrong,
        'setting-dictation-mode': s.continuousMode,
        'setting-shuffle': s.shufflePlay,
        'setting-auto-submit': s.autoSubmit,
        'setting-error-book': s.errorBook
    };
    
    for (const [id, checked] of Object.entries(checkboxes)) {
        const el = document.getElementById(id);
        if (el) el.checked = checked;
    }
    
    // Selects
    const selects = {
        'setting-playback-speed': s.playSpeed.toString(),
        'setting-playback-count': s.playCount.toString(),
        'setting-volume': s.volume.toString(),
        'setting-voice': s.voice,
        'setting-interval': s.interval.toString(),
        'setting-theme': s.theme,
        'setting-font-size': s.fontSize,
        'setting-review-interval': s.reviewInterval.toString(),
        'setting-review-limit': s.reviewLimit.toString()
    };
    
    for (const [id, value] of Object.entries(selects)) {
        const el = document.getElementById(id);
        if (el) el.value = value;
    }
}

// ========== MODE SWITCHING ==========
function initModeSelector() {
    const modeBtn = document.getElementById('modeBtn');
    const modeDropdown = document.getElementById('modeDropdown');
    const modeOptions = document.querySelectorAll('.mode-dropdown-item');
    
    if (!modeBtn || !modeDropdown) return;
    
    // Toggle dropdown
    modeBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        modeDropdown.classList.toggle('hidden');
        document.getElementById('dayDropdown')?.classList.add('hidden');
    });
    
    // Mode selection
    modeOptions.forEach(option => {
        option.addEventListener('click', () => {
            const mode = option.dataset.mode;
            switchMode(mode);
            modeDropdown.classList.add('hidden');
        });
    });
    
    // Close on outside click
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.header-right') && !e.target.closest('#modeBtn')) {
            modeDropdown.classList.add('hidden');
        }
    });
}

function switchMode(mode) {
    state.mode = mode;
    
    // Update UI
    const modeText = document.getElementById('modeText');
    const modeOptions = document.querySelectorAll('.mode-dropdown-item');
    
    if (modeText) {
        const modeNames = {
            'smart': '智能模式',
            'dictation': '听写模式',
            'listening': '听音选义',
            'radio': '随身听',
            'blind': '默写模式'
        };
        modeText.textContent = modeNames[mode] || '听音选义';
    }
    
    modeOptions.forEach(opt => {
        opt.classList.toggle('active', opt.dataset.mode === mode);
    });
    
    // Update mode display if exists
    const currentMode = document.getElementById('currentMode');
    if (currentMode) {
        currentMode.classList.toggle('listening', mode === 'listening');
        currentMode.classList.toggle('dictation', mode === 'dictation');
    }
    
    // Save mode preference
    state.settings.currentMode = mode;
    saveSettings();
    
    // Setup mode-specific UI
    setupModeUI();
    
    // If in practice, restart with new mode
    if (document.getElementById('practicePage')?.classList.contains('active')) {
        state.currentIndex = 0;
        state.correctCount = 0;
        state.wrongCount = 0;
        initSmartModeSequence();
        if (state.settings.shufflePlay) {
            shuffleVocabulary();
        } else {
            state.shuffledVocabulary = [...state.vocabulary];
        }
        updateWordDisplay();
    }
}

function setupModeUI() {
    const optionsGrid = document.getElementById('optionsGrid');
    const wordDisplay = document.getElementById('wordDisplay');
    const inputArea = document.getElementById('inputArea');
    
    // Hide all mode-specific elements first
    if (optionsGrid) optionsGrid.innerHTML = '';
    
    // Reset common elements visibility
    const playBtn = document.getElementById('playBtn');
    if (playBtn) playBtn.style.display = 'flex';
    
    // Mode-specific UI setup
    switch (state.mode) {
        case 'smart':
            // Smart mode shows options grid
            break;
            
        case 'dictation':
        case 'blind':
            // Show input for spelling
            if (optionsGrid) {
                optionsGrid.innerHTML = `
                    <div class="spelling-input-area">
                        <input type="text" class="spelling-input" id="spellingInput" 
                               placeholder="请拼写听到的单词" autocomplete="off" spellcheck="false">
                        <button class="spelling-submit" id="spellingSubmit">提交</button>
                    </div>
                `;
                setupSpellingInput();
            }
            break;
            
        case 'listening':
            // Shows 2x2 options grid (default)
            break;
            
        case 'radio':
            // Just play, no interaction
            if (optionsGrid) {
                optionsGrid.innerHTML = `
                    <div class="portable-message">
                        <p>点击播放按钮开始听写</p>
                        <p class="portable-tip">只播放不答题</p>
                    </div>
                `;
            }
            break;
    }
}

// ========== SPELLING INPUT ==========
function setupSpellingInput() {
    const input = document.getElementById('spellingInput');
    const submit = document.getElementById('spellingSubmit');
    
    if (!input || !submit) return;
    
    input.focus();
    
    submit.addEventListener('click', () => checkSpelling());
    
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            checkSpelling();
        }
    });
}

function checkSpelling() {
    if (state.isAnswered) return;
    
    const input = document.getElementById('spellingInput');
    if (!input) return;
    
    const userAnswer = input.value.trim().toLowerCase();
    const currentWord = state.shuffledVocabulary[state.currentIndex];
    
    if (!currentWord || !userAnswer) return;
    
    state.isAnswered = true;
    
    const isCorrect = userAnswer === currentWord.word.toLowerCase();
    
    if (isCorrect) {
        handleCorrectAnswer();
    } else {
        handleWrongAnswer();
        
        // Show correct answer if setting enabled
        if (state.settings.showAnswerOnWrong) {
            showCorrectAnswer();
            input.value = '';
            input.placeholder = `正确答案: ${currentWord.word}`;
            input.classList.add('show-answer');
            state.isAnswered = false;
            
            // Auto advance when correct
            if (state.settings.autoSubmit) {
                input.addEventListener('input', function checkAutoSubmit() {
                    if (input.value.trim().toLowerCase() === currentWord.word.toLowerCase()) {
                        handleCorrectAnswer();
                        input.removeEventListener('input', checkAutoSubmit);
                    }
                }, { once: true });
            }
        }
    }
}

function showCorrectAnswer() {
    const currentWord = state.shuffledVocabulary[state.currentIndex];
    const input = document.getElementById('spellingInput');
    if (input && currentWord) {
        input.placeholder = `正确答案: ${currentWord.word} (${currentWord.pos}) ${currentWord.definition}`;
    }
}

// ========== DAY SELECTOR ==========
function initDaySelector() {
    const dayBtn = document.getElementById('daySelector');
    const dayDropdown = document.getElementById('dayDropdown');
    
    if (!dayBtn || !dayDropdown) return;
    
    // Generate day grid
    for (let day = 1; day <= 30; day++) {
        const dayItem = document.createElement('div');
        dayItem.className = 'day-dropdown-item';
        dayItem.dataset.day = day;
        
        const label = document.createElement('span');
        label.className = 'day-label';
        label.textContent = `Day ${day}`;
        
        dayItem.appendChild(label);
        
        dayItem.addEventListener('click', () => {
            selectDay(day);
            dayDropdown.classList.add('hidden');
        });
        
        dayDropdown.appendChild(dayItem);
    }
    
    // Toggle dropdown
    dayBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        dayDropdown.classList.toggle('hidden');
        document.getElementById('modeDropdown')?.classList.add('hidden');
    });
    
    // Close on outside click
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.header-center') && !e.target.closest('#daySelector')) {
            dayDropdown.classList.add('hidden');
        }
    });
}

function selectDay(day) {
    state.currentDay = day;
    
    // Update display
    const dayDisplay = document.getElementById('daySelectorCurrent');
    if (dayDisplay) {
        dayDisplay.textContent = `超核心词汇 Day ${day}`;
    }
    
    // Update active state in dropdown
    document.querySelectorAll('.day-dropdown-item').forEach(item => {
        item.classList.toggle('active', parseInt(item.dataset.day) === day);
    });
    
    // If in practice, restart with new day
    if (document.getElementById('practicePage')?.classList.contains('active')) {
        startPractice(day);
    }
}

// ========== SETTINGS PANEL ==========
function initSettingsPanel() {
    const settingsBtn = document.getElementById('settingsBtn');
    const settingsOverlay = document.getElementById('settingsOverlay');
    const settingsClose = document.getElementById('settingsClose');
    const settingsCloseBtn = document.getElementById('settingsCloseBtn');
    
    // Open settings
    if (settingsBtn) {
        settingsBtn.addEventListener('click', () => {
            openSettingsPanel();
        });
    }
    
    // Close settings
    const closeHandler = () => closeSettingsPanel();
    if (settingsOverlay) {
        settingsOverlay.addEventListener('click', (e) => {
            if (e.target === settingsOverlay) closeHandler();
        });
    }
    if (settingsClose) settingsClose.addEventListener('click', closeHandler);
    if (settingsCloseBtn) settingsCloseBtn.addEventListener('click', closeHandler);
    
    // Settings tabs
    const settingsTabs = document.querySelectorAll('.settings-tab');
    settingsTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.dataset.tab;
            switchSettingsTab(tabName);
        });
    });
    
    // Settings controls
    initSettingsControls();
}

function openSettingsPanel() {
    const overlay = document.getElementById('settingsOverlay');
    const modal = overlay?.querySelector('.settings-modal');
    if (overlay) overlay.classList.add('show');
    if (modal) modal.classList.add('show');
    updateSettingsUI();
}

function closeSettingsPanel() {
    const overlay = document.getElementById('settingsOverlay');
    const modal = overlay?.querySelector('.settings-modal');
    if (overlay) overlay.classList.remove('show');
    if (modal) modal.classList.remove('show');
}

function switchSettingsTab(tabName) {
    const tabs = document.querySelectorAll('.settings-tab');
    const panels = document.querySelectorAll('.settings-panel');
    
    tabs.forEach(t => t.classList.toggle('active', t.dataset.tab === tabName));
    panels.forEach(p => p.classList.toggle('active', p.id === `panel-${tabName}`));
}

function initSettingsControls() {
    // Checkbox settings
    const checkboxSettings = [
        'setting-repeat-wrong',
        'setting-show-answer',
        'setting-dictation-mode',
        'setting-shuffle',
        'setting-auto-submit',
        'setting-error-book'
    ];
    
    checkboxSettings.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('change', () => {
                const settingName = id.replace('setting-', '').replace(/-([a-z])/g, (_, c) => c.toUpperCase());
                state.settings[settingName] = el.checked;
                saveSettings();
            });
        }
    });
    
    // Dark mode toggle (special handling)
    const darkModeToggle = document.getElementById('darkMode');
    if (darkModeToggle) {
        darkModeToggle.checked = state.settings.theme === 'dark';
        darkModeToggle.addEventListener('change', () => {
            state.settings.theme = darkModeToggle.checked ? 'dark' : 'light';
            applySettings();
            saveSettings();
        });
    }
    
    // Select settings
    const selectSettings = [
        { id: 'setting-playback-speed', key: 'playSpeed', parse: parseFloat },
        { id: 'setting-playback-count', key: 'playCount', parse: parseInt },
        { id: 'setting-volume', key: 'volume', parse: parseInt },
        { id: 'setting-voice', key: 'voice' },
        { id: 'setting-interval', key: 'interval', parse: parseInt },
        { id: 'setting-theme', key: 'theme' },
        { id: 'setting-font-size', key: 'fontSize' },
        { id: 'setting-review-interval', key: 'reviewInterval', parse: parseInt },
        { id: 'setting-review-limit', key: 'reviewLimit', parse: parseInt }
    ];
    
    selectSettings.forEach(({ id, key, parse }) => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('change', () => {
                state.settings[key] = parse ? parse(el.value) : el.value;
                saveSettings();
            });
        }
    });
}

// ========== SHUFFLE PLAY (Fisher-Yates) ==========
function shuffleArray(array) {
    const shuffled = [...array];
    for (let i = shuffled.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    return shuffled;
}

function shuffleVocabulary() {
    state.shuffledVocabulary = shuffleArray(state.vocabulary);
    state.wrongWordQueue = [];
}

// ========== WRONG WORD LOOP ==========
function recordWrongWord(wordId) {
    if (!state.settings.wrongWordLoop) return;
    
    if (!state.wrongWords[wordId]) {
        state.wrongWords[wordId] = { count: 0, streak: 0 };
    }
    
    state.wrongWords[wordId].count++;
    state.wrongWords[wordId].streak = 0;
    
    // Add to queue if not already there
    if (!state.wrongWordQueue.includes(wordId)) {
        state.wrongWordQueue.push(wordId);
    }
}

function recordCorrectWord(wordId) {
    if (!state.settings.wrongWordLoop) return;
    
    if (state.wrongWords[wordId]) {
        state.wrongWords[wordId].streak++;
        
        // Remove from queue if streak >= 2
        if (state.wrongWords[wordId].streak >= 2) {
            const idx = state.wrongWordQueue.indexOf(wordId);
            if (idx > -1) {
                state.wrongWordQueue.splice(idx, 1);
            }
        }
    }
}

function getNextWrongWord() {
    if (state.wrongWordQueue.length === 0) return null;
    
    const wordId = state.wrongWordQueue[0];
    return state.shuffledVocabulary.find(w => w.id === wordId);
}

// ========== SMART MODE ==========
function initSmartModeSequence() {
    // Create a mixed sequence of different modes
    const modes = ['meaning', 'listening', 'spelling'];
    state.smartModeSequence = [];
    
    for (let i = 0; i < 30; i++) {
        state.smartModeSequence.push(modes[i % 3]);
    }
    
    state.smartModeIndex = 0;
}

function getSmartMode() {
    if (state.smartModeIndex >= state.smartModeSequence.length) {
        state.smartModeIndex = 0;
    }
    return state.smartModeSequence[state.smartModeIndex++];
}

// ========== PLAY CONTROL ==========
function playCurrentWord() {
    if (!('speechSynthesis' in window)) return;
    
    speechSynthesis.cancel();
    const word = state.shuffledVocabulary[state.currentIndex];
    if (!word) return;
    
    state.isPlaying = true;
    
    const playWord = () => {
        const utterance = new SpeechSynthesisUtterance(word.word);
        utterance.lang = 'en-GB';
        utterance.rate = state.settings.playSpeed;
        utterance.volume = state.settings.volume / 100;
        
        utterance.onend = () => {
            // Continue playing if more counts
            const currentCount = parseInt(utterance.dataset.playCount || '0');
            if (currentCount < state.settings.playCount - 1) {
                utterance.dataset.playCount = (currentCount + 1).toString();
                setTimeout(playWord, 500);
            } else {
                state.isPlaying = false;
                
                // Auto advance in continuous mode
                if (state.settings.continuousMode && state.mode !== 'portable') {
                    setTimeout(() => {
                        if (!state.isAnswered) {
                            handleTimeout();
                        }
                    }, state.settings.interval * 1000);
                }
            }
        };
        
        speechSynthesis.speak(utterance);
    };
    
    playWord();
    
    // Update play button state
    const playBtn = document.getElementById('playBtn');
    if (playBtn) playBtn.classList.add('playing');
}

function stopPlaying() {
    speechSynthesis.cancel();
    state.isPlaying = false;
    const playBtn = document.getElementById('playBtn');
    if (playBtn) playBtn.classList.remove('playing');
}

// ========== KEYBOARD SHORTCUTS ==========
function initKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Only handle if in practice page
        if (!document.getElementById('practicePage')?.classList.contains('active')) return;
        if (state.isAnswered && state.mode !== 'dictation' && state.mode !== 'blind') return;
        
        const keyMap = { '1': 0, '2': 1, '3': 2, '4': 3, '5': 4 };
        
        // Mode-specific handling
        if (state.mode === 'listening' || state.mode === 'smart' || state.mode === 'meaning') {
            if (keyMap.hasOwnProperty(e.key)) {
                selectOption(keyMap[e.key]);
            } else if (e.key === '5') {
                // "Don't know" - treat as wrong
                handleDontKnow();
            }
        } else if (state.mode === 'dictation' || state.mode === 'blind') {
            // Enter to submit spelling
            if (e.key === 'Enter') {
                checkSpelling();
            }
        }
        
        // Space to play/replay
        if (e.code === 'Space' && !e.target.matches('input')) {
            e.preventDefault();
            playCurrentWord();
        }
    });
}

function handleDontKnow() {
    if (state.isAnswered) return;
    state.isAnswered = true;
    state.wrongCount++;
    
    const currentWord = state.shuffledVocabulary[state.currentIndex];
    recordWrongWord(currentWord.id);
    
    // Show correct answer
    const buttons = document.querySelectorAll('.option-btn');
    buttons.forEach(btn => {
        btn.disabled = true;
        if (btn.dataset.correct === 'true') {
            btn.classList.add('correct');
        }
    });
    
    // Show previous word
    showPreviousWord();
    
    document.getElementById('wrongCount').textContent = state.wrongCount;
    saveProgress();
    
    // Auto advance
    setTimeout(() => {
        nextWord();
    }, 2000);
}

// ========== INIT ==========
document.addEventListener('DOMContentLoaded', async () => {
    // Load settings first
    loadSettings();
    
    // Apply saved mode
    if (state.settings.currentMode) {
        state.mode = state.settings.currentMode;
    }
    
    // Check for existing token
    const savedToken = localStorage.getItem('auth_token');
    const savedUser = localStorage.getItem('auth_user');

    if (savedToken && savedUser) {
        try {
            state.token = savedToken;
            state.user = JSON.parse(savedUser);

            // Verify token is still valid
            const data = await apiRequest('/auth/me');
            state.user = data.user;
            localStorage.setItem('auth_user', JSON.stringify(state.user));

            await loadProgress();
            showHomePage();
            setupEventListeners();
            
            // Initialize UI state
            updateModeDisplay();
            updateDayDisplay();
            
            console.log('Session restored successfully');
            return;
        } catch (e) {
            console.log('Session restoration failed:', e);
        }
    }

    showAuthPage();
    setupEventListeners();
    
    // Initialize UI state
    updateModeDisplay();
    updateDayDisplay();
});

// Helper to update mode display on load
function updateModeDisplay() {
    const modeText = document.getElementById('modeText');
    const modeOptions = document.querySelectorAll('.mode-dropdown-item');
    
    if (modeText) {
        const modeNames = {
            'smart': '智能模式',
            'dictation': '听写模式',
            'listening': '听音选义',
            'radio': '随身听',
            'blind': '默写模式'
        };
        modeText.textContent = modeNames[state.mode] || '听音选义';
    }
    
    modeOptions.forEach(opt => {
        opt.classList.toggle('active', opt.dataset.mode === state.mode);
    });
}

function updateDayDisplay() {
    const dayDisplay = document.getElementById('daySelectorCurrent');
    if (dayDisplay) {
        dayDisplay.textContent = `超核心词汇 Day ${state.currentDay}`;
    }
}

// ========== EVENT LISTENERS ==========
function setupEventListeners() {
    // Initialize UI components
    initModeSelector();
    initDaySelector();
    initSettingsPanel();
    initKeyboardShortcuts();
    
    // Auth
    document.getElementById('authBtn')?.addEventListener('click', handleAuth);
    document.getElementById('switchAuthBtn')?.addEventListener('click', toggleAuthMode);
    document.getElementById('logoutBtn')?.addEventListener('click', handleLogout);

    // User menu
    document.getElementById('userBtn')?.addEventListener('click', () => {
        if (state.user) {
            document.getElementById('userDropdown')?.classList.toggle('show');
        }
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.user-menu')) {
            document.getElementById('userDropdown')?.classList.remove('show');
        }
    });

    // Mode tabs (legacy compatibility)
    document.querySelectorAll('.mode-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.mode-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            state.learningMode = tab.dataset.mode;

            if (state.learningMode === 'listening') {
                playCurrentWord();
            }
        });
    });

    // Play button
    document.getElementById('playBtn')?.addEventListener('click', playCurrentWord);

    // Exit button
    document.getElementById('exitBtn')?.addEventListener('click', exitPractice);
    
    // Home button
    document.getElementById('homeBtn')?.addEventListener('click', () => {
        exitPractice();
    });

    // Complete screen buttons
    document.getElementById('backHomeBtn')?.addEventListener('click', () => {
        document.getElementById('completeScreen')?.classList.remove('active');
        document.getElementById('practicePage')?.classList.remove('active');
        showHomePage();
    });

    document.getElementById('nextDayBtn')?.addEventListener('click', () => {
        if (state.currentDay < 30) {
            state.currentDay++;
            startPractice(state.currentDay);
        }
    });
}

// ========== AUTH ==========
function toggleAuthMode() {
    state.isLoginMode = !state.isLoginMode;
    document.getElementById('authTitle').textContent = state.isLoginMode ? '登录' : '注册';
    document.getElementById('authSubtitle').textContent = state.isLoginMode ? '登录后自动同步学习进度' : '注册账号开始学习';
    document.getElementById('authBtn').textContent = state.isLoginMode ? '登录' : '注册';
    document.getElementById('switchAuthBtn').textContent = state.isLoginMode ? '注册账号' : '登录账号';

    // Show/hide username and confirm password fields for registration
    document.getElementById('usernameField').style.display = state.isLoginMode ? 'none' : 'block';
    document.getElementById('confirmPasswordField').style.display = state.isLoginMode ? 'none' : 'block';

    // Clear form fields when switching
    document.getElementById('usernameInput').value = '';
    document.getElementById('emailInput').value = '';
    document.getElementById('passwordInput').value = '';
    document.getElementById('confirmPasswordInput').value = '';
}

// Validate email format
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

async function handleAuth() {
    const email = document.getElementById('emailInput').value.trim();
    const password = document.getElementById('passwordInput').value;
    const username = document.getElementById('usernameInput').value.trim();
    const confirmPassword = document.getElementById('confirmPasswordInput').value;
    const agreement = document.getElementById('agreement');

    if (!email || !password) {
        showToast('请输入邮箱和密码');
        return;
    }

    // Check agreement checkbox
    if (agreement && !agreement.checked) {
        showToast('请先阅读并同意用户服务协议');
        return;
    }

    // Registration validation
    if (!state.isLoginMode) {
        if (!username || username.length < 3) {
            showToast('用户名至少需要3个字符');
            return;
        }
        if (password.length < 6) {
            showToast('密码至少需要6位');
            return;
        }
        if (password !== confirmPassword) {
            showToast('两次输入的密码不一致');
            return;
        }
        if (!isValidEmail(email)) {
            showToast('请输入有效的邮箱地址');
            return;
        }
    }

    try {
        let result;
        if (state.isLoginMode) {
            // Login
            result = await apiRequest('/auth/login', {
                method: 'POST',
                body: JSON.stringify({ email, password })
            });
        } else {
            // Register
            result = await apiRequest('/auth/register', {
                method: 'POST',
                body: JSON.stringify({ email, password, username })
            });
        }

        // Save token and user
        state.token = result.token;
        state.user = result.user;

        localStorage.setItem('auth_token', result.token);
        localStorage.setItem('auth_user', JSON.stringify(result.user));

        showToast(state.isLoginMode ? '登录成功' : '注册成功');
        showHomePage();
    } catch (error) {
        showToast(error.message);
    }
}

async function handleLogout() {
    try {
        await apiRequest('/auth/logout', {
            method: 'POST'
        });
    } catch (e) {
        // Ignore logout errors
    }

    state.user = null;
    state.token = null;
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_user');

    showAuthPage();
    document.getElementById('userDropdown')?.classList.remove('show');
}

// ========== PAGES ==========
function showAuthPage() {
    document.getElementById('authPage').style.display = 'flex';
    document.getElementById('homePage')?.classList.add('hidden');
    document.getElementById('practicePage')?.classList.remove('active');
    document.getElementById('completeScreen')?.classList.remove('active');
    
    const userInitial = document.getElementById('userInitial');
    if (userInitial) userInitial.textContent = '?';
    
    const progressIndicator = document.getElementById('progressIndicator');
    if (progressIndicator) progressIndicator.textContent = '';
    
    const progressText = document.getElementById('progressText');
    if (progressText) progressText.textContent = '0/100';
}

function showHomePage() {
    document.getElementById('authPage').style.display = 'none';
    document.getElementById('homePage')?.classList.remove('hidden');
    document.getElementById('practicePage')?.classList.remove('active');
    document.getElementById('completeScreen')?.classList.remove('active');

    if (state.user) {
        const userInitial = document.getElementById('userInitial');
        if (userInitial) {
            userInitial.textContent = state.user.username ? state.user.username[0].toUpperCase() : state.user.email[0].toUpperCase();
        }
        
        const progressIndicator = document.getElementById('progressIndicator');
        if (progressIndicator) {
            progressIndicator.textContent = `Day ${state.currentDay}`;
        }
    }

    renderDayGrid();
}

function renderDayGrid() {
    const grid = document.getElementById('dayGrid');
    grid.innerHTML = '';

    for (let day = 1; day <= 30; day++) {
        const card = document.createElement('div');
        card.className = 'day-card';

        // Check if completed (current_index >= 100 means finished)
        const progress = state.userProgress[day];
        const isCompleted = progress && progress.current_index >= 100;
        if (isCompleted) card.classList.add('completed');

        card.innerHTML = `
            <div class="day-number">Day ${day}</div>
            <div class="day-status">${isCompleted ? '已完成' : progress ? `${progress.current_index}/100` : '100 单词'}</div>
        `;

        card.addEventListener('click', () => startPractice(day));
        grid.appendChild(card);
    }
}

async function startPractice(day) {
    state.currentDay = day;
    state.isAnswered = false;
    state.currentWrongWordStreak = 0;

    // Get saved progress or start from beginning
    const savedProgress = state.userProgress[day];
    if (savedProgress && savedProgress.current_index >= 100) {
        // Day already completed, start from beginning
        state.currentIndex = 0;
        state.correctCount = 0;
        state.wrongCount = 0;
    } else if (savedProgress) {
        // Continue from saved progress
        state.currentIndex = savedProgress.current_index || 0;
        state.correctCount = savedProgress.correct_count || 0;
        state.wrongCount = savedProgress.wrong_count || 0;
    } else {
        // New day
        state.currentIndex = 0;
        state.correctCount = 0;
        state.wrongCount = 0;
    }

    // Get vocabulary for this day
    state.vocabulary = vocabularyData.filter(v => v.day === day);
    
    // Apply shuffle if enabled
    if (state.settings.shufflePlay) {
        shuffleVocabulary();
    } else {
        state.shuffledVocabulary = [...state.vocabulary];
    }
    
    // Initialize smart mode
    initSmartModeSequence();

    document.getElementById('homePage')?.classList.add('hidden');
    document.getElementById('practicePage')?.classList.add('active');
    document.getElementById('completeScreen')?.classList.remove('active');
    document.getElementById('previousWord')?.classList.remove('show');

    const progressIndicator = document.getElementById('progressIndicator');
    if (progressIndicator) {
        progressIndicator.textContent = `Day ${day} - ${state.currentIndex + 1}/100`;
    }
    
    const progressText = document.getElementById('progressText');
    if (progressText) {
        progressText.textContent = `${state.currentIndex + 1}/100`;
    }

    // Setup mode-specific UI
    setupModeUI();
    updateWordDisplay();
}

function updateWordDisplay() {
    if (state.currentIndex >= state.shuffledVocabulary.length) {
        showCompleteScreen();
        return;
    }

    const word = state.shuffledVocabulary[state.currentIndex];

    document.getElementById('currentWord').textContent = word.word;
    document.getElementById('wordPhonetic').textContent = word.phonetic;
    document.getElementById('wordPos').textContent = word.pos;
    document.getElementById('progressFill').style.width = `${(state.currentIndex / state.shuffledVocabulary.length) * 100}%`;
    document.getElementById('correctCount').textContent = state.correctCount;
    document.getElementById('wrongCount').textContent = state.wrongCount;
    
    const progressIndicator = document.getElementById('progressIndicator');
    if (progressIndicator) {
        progressIndicator.textContent = `Day ${state.currentDay} - ${state.currentIndex + 1}/100`;
    }
    
    const progressText = document.getElementById('progressText');
    if (progressText) {
        progressText.textContent = `${state.currentIndex + 1}/${state.shuffledVocabulary.length}`;
    }

    state.isAnswered = false;
    
    // Clear spelling input if in spelling mode
    const spellingInput = document.getElementById('spellingInput');
    if (spellingInput) {
        spellingInput.value = '';
        spellingInput.placeholder = '请拼写听到的单词';
        spellingInput.classList.remove('show-answer');
    }

    // Generate content based on mode
    if (state.mode === 'listening' || state.mode === 'smart') {
        generateOptions(word);
    } else if (state.mode === 'dictation' || state.mode === 'blind') {
        // Focus on input
        setTimeout(() => {
            document.getElementById('spellingInput')?.focus();
        }, 100);
    }

    // Auto play in listening modes
    if (state.mode === 'listening' || state.mode === 'dictation' || state.mode === 'blind' || state.mode === 'smart') {
        setTimeout(playCurrentWord, 500);
    }
}

function generateOptions(currentWord) {
    const grid = document.getElementById('optionsGrid');
    grid.innerHTML = '';

    // Get 3 random wrong definitions
    const otherWords = state.shuffledVocabulary.filter(w => w.id !== currentWord.id);
    const shuffled = shuffleArray(otherWords);
    const wrongOptions = shuffled.slice(0, 3).map(w => w.definition);

    // Combine with correct answer and shuffle
    const options = [
        { text: currentWord.definition, correct: true, pos: currentWord.pos },
        ...wrongOptions.map(text => ({ text, correct: false, pos: '' }))
    ].sort(() => Math.random() - 0.5);

    options.forEach((opt, idx) => {
        const btn = document.createElement('button');
        btn.className = 'option-btn';
        btn.dataset.correct = opt.correct;
        btn.innerHTML = `<span class="option-pos">${opt.pos}</span><span class="option-text">${opt.text}</span><span class="hotkey">${idx + 1}</span>`;
        btn.addEventListener('click', () => selectOption(idx));
        grid.appendChild(btn);
    });
}

function selectOption(idx) {
    if (state.isAnswered) return;
    state.isAnswered = true;

    const buttons = document.querySelectorAll('.option-btn');
    const currentWord = state.shuffledVocabulary[state.currentIndex];
    const selectedBtn = buttons[idx];
    const isCorrect = selectedBtn.dataset.correct === 'true';

    // Disable all buttons
    buttons.forEach(btn => btn.disabled = true);

    if (isCorrect) {
        selectedBtn.classList.add('correct');
        state.correctCount++;
        handleCorrectAnswer();
    } else {
        selectedBtn.classList.add('wrong');
        state.wrongCount++;
        
        recordWrongWord(currentWord.id);
        
        // Show correct answer
        buttons.forEach(btn => {
            if (btn.dataset.correct === 'true') {
                btn.classList.add('correct');
            }
        });
        
        handleWrongAnswer();
    }

    // Show previous word
    showPreviousWord();

    // Update stats
    document.getElementById('correctCount').textContent = state.correctCount;
    document.getElementById('wrongCount').textContent = state.wrongCount;

    // Save progress
    saveProgress();

    // Auto advance after 2 seconds
    setTimeout(() => {
        nextWord();
    }, 2000);
}

function handleCorrectAnswer() {
    const currentWord = state.shuffledVocabulary[state.currentIndex];
    recordCorrectWord(currentWord.id);
}

function handleWrongAnswer() {
    // Additional wrong answer handling if needed
}

function showPreviousWord() {
    if (state.currentIndex > 0) {
        const prevWord = state.shuffledVocabulary[state.currentIndex - 1];
        document.getElementById('prevWord').textContent = prevWord.word;
        document.getElementById('prevPhonetic').textContent = prevWord.phonetic;
        document.getElementById('prevPos').textContent = prevWord.pos;
        document.getElementById('prevDefinition').textContent = prevWord.definition;
        document.getElementById('previousWord')?.classList.add('show');
    }
}

function nextWord() {
    // Check for wrong word loop
    if (state.settings.wrongWordLoop && state.wrongWordQueue.length > 0) {
        const nextWrong = getNextWrongWord();
        if (nextWrong) {
            // Insert wrong word after current position
            state.shuffledVocabulary.splice(state.currentIndex + 1, 0, nextWrong);
        }
    }
    
    state.currentIndex++;
    updateWordDisplay();
}

function handleTimeout() {
    // User didn't answer in time - treat as wrong
    if (!state.isAnswered) {
        state.isAnswered = true;
        state.wrongCount++;
        
        const currentWord = state.shuffledVocabulary[state.currentIndex];
        recordWrongWord(currentWord.id);
        
        // Show correct answer
        const buttons = document.querySelectorAll('.option-btn');
        buttons.forEach(btn => {
            btn.disabled = true;
            if (btn.dataset.correct === 'true') {
                btn.classList.add('correct');
            }
        });
        
        document.getElementById('wrongCount').textContent = state.wrongCount;
        saveProgress();
        
        setTimeout(() => {
            nextWord();
        }, 2000);
    }
}

function showCompleteScreen() {
    document.getElementById('practicePage')?.classList.remove('active');
    document.getElementById('completeScreen')?.classList.add('active');

    document.getElementById('completedDay').textContent = state.currentDay;
    document.getElementById('finalCorrect').textContent = state.correctCount;
    document.getElementById('finalWrong').textContent = state.wrongCount;

    // Mark day as completed
    if (!state.userProgress[state.currentDay]) {
        state.userProgress[state.currentDay] = {};
    }
    state.userProgress[state.currentDay].current_index = 100;
    state.userProgress[state.currentDay].correct_count = state.correctCount;
    state.userProgress[state.currentDay].wrong_count = state.wrongCount;
    saveProgress();
}

function exitPractice() {
    document.getElementById('practicePage')?.classList.remove('active');
    document.getElementById('completeScreen')?.classList.remove('active');
    stopPlaying();
    showHomePage();
}

// ========== DATA STORAGE ==========
async function saveProgress() {
    if (!state.user || !state.token) return;

    try {
        await apiRequest('/progress', {
            method: 'POST',
            body: JSON.stringify({
                day: state.currentDay,
                current_index: state.currentIndex,
                correct_count: state.correctCount,
                wrong_count: state.wrongCount
            })
        });
    } catch (error) {
        console.error('Error saving progress:', error);
    }
}

async function loadProgress() {
    if (!state.user || !state.token) return;

    try {
        const data = await apiRequest('/progress');

        if (data.progress) {
            data.progress.forEach(p => {
                state.userProgress[p.day] = p;
            });

            // Find current day
            const maxDay = Math.max(...Object.keys(state.userProgress).map(Number), 1);
            state.currentDay = maxDay;
        }
    } catch (error) {
        console.error('Error loading progress:', error);
    }
}

// ========== UTILS ==========
function showToast(message) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 3000);
}
