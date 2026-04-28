const PRD_UI_CACHE_VERSION = '20260429-magic-ui-1'

function assetPath(path: string): string {
  const base = import.meta.env.BASE_URL || '/'
  const normalizedBase = base.endsWith('/') ? base : `${base}/`
  const cleanPath = path.replace(/^\/+/, '')
  return `${normalizedBase}${cleanPath}?v=${PRD_UI_CACHE_VERSION}`
}

export function prdTemplateAsset(path: string): string {
  return assetPath(path)
}

export const prdUiAsset = {
  background: {
    mapEducation: assetPath('/ui/background/map_education.png'),
    mapEnvironment: assetPath('/ui/background/map_environment.png'),
    classroomBlur: assetPath('/ui/background/classroom_blur.png'),
    resultDimOverlay: assetPath('/ui/background/result_dim_overlay.png'),
  },
  templates: {
    learningCenter: prdTemplateAsset('/ui/templates/learning-center-text-safe.png'),
    wordChainMap: prdTemplateAsset('/ui/templates/word-chain-map-text-safe.png'),
    mobileWordChainMap: prdTemplateAsset('/ui/templates/mobile-word-chain-map-text-safe.png'),
    wordMission: prdTemplateAsset('/ui/templates/word-mission-text-safe.png'),
    refillState: prdTemplateAsset('/ui/templates/refill-state-text-safe.png'),
    stageSettlement: prdTemplateAsset('/ui/templates/stage-settlement-text-safe.png'),
    mobileWordMission: prdTemplateAsset('/ui/templates/mobile-word-mission-text-safe.png'),
  },
  hud: {
    avatarFrame: assetPath('/ui/hud/avatar_frame.png'),
    resourcePill: assetPath('/ui/hud/resource_pill.png'),
    iconEnergy: assetPath('/ui/hud/icon_energy.png'),
    iconCoin: assetPath('/ui/hud/icon_coin.png'),
    iconGem: assetPath('/ui/hud/icon_gem.png'),
    iconMail: assetPath('/ui/hud/icon_mail.png'),
  },
  map: {
    levelBadgeBlue: assetPath('/ui/map/level_badge_blue.png'),
    levelBadgeGray: assetPath('/ui/map/level_badge_gray.png'),
    levelBadgeGold: assetPath('/ui/map/level_badge_gold.png'),
    levelBadgeLocked: assetPath('/ui/map/level_badge_locked.png'),
    starFull: assetPath('/ui/map/star_full.png'),
    starEmpty: assetPath('/ui/map/star_empty.png'),
    treasureClosed: assetPath('/ui/map/treasure_closed.png'),
    treasureOpen: assetPath('/ui/map/treasure_open.png'),
    nodeCurrent: assetPath('/ui/map/node_current.png'),
    nodeBoss: assetPath('/ui/map/node_boss.png'),
  },
  cards: {
    languageUse: assetPath('/ui/cards/card_language_use.png'),
    listening: assetPath('/ui/cards/card_listening.png'),
    reading: assetPath('/ui/cards/card_reading.png'),
    speaking: assetPath('/ui/cards/card_speaking.png'),
    writing: assetPath('/ui/cards/card_writing.png'),
  },
  buttons: {
    green: assetPath('/ui/buttons/btn_green.png'),
    blue: assetPath('/ui/buttons/btn_blue.png'),
    purple: assetPath('/ui/buttons/btn_purple.png'),
    gold: assetPath('/ui/buttons/btn_gold.png'),
    red: assetPath('/ui/buttons/btn_red.png'),
    disabled: assetPath('/ui/buttons/btn_disabled.png'),
    focusGlow: assetPath('/ui/buttons/btn_focus_glow.png'),
  },
  modal: {
    panelResult: assetPath('/ui/modal/panel_result.png'),
    panelReport: assetPath('/ui/modal/panel_report.png'),
    parchmentTitle: assetPath('/ui/modal/parchment_title.png'),
    goldenMedal: assetPath('/ui/modal/golden_medal.png'),
  },
  icons: {
    abc: assetPath('/ui/icons/icon_abc.png'),
    sound: assetPath('/ui/icons/icon_sound.png'),
    book: assetPath('/ui/icons/icon_book.png'),
    microphone: assetPath('/ui/icons/icon_microphone.png'),
    pen: assetPath('/ui/icons/icon_pen.png'),
    bag: assetPath('/ui/icons/icon_bag.png'),
    task: assetPath('/ui/icons/icon_task.png'),
    achievement: assetPath('/ui/icons/icon_achievement.png'),
    shop: assetPath('/ui/icons/icon_shop.png'),
    rank: assetPath('/ui/icons/icon_rank.png'),
    setting: assetPath('/ui/icons/icon_setting.png'),
    back: assetPath('/ui/icons/icon_back.png'),
  },
} as const

function flattenAssetPaths(value: unknown): string[] {
  if (typeof value === 'string') return [value]
  if (!value || typeof value !== 'object') return []
  return Object.values(value).flatMap(flattenAssetPaths)
}

export const prdUiAssetList = flattenAssetPaths(prdUiAsset)
