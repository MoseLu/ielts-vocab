export const prdUiAsset = {
  background: {
    mapEducation: '/ui/background/map_education.png',
    mapEnvironment: '/ui/background/map_environment.png',
    classroomBlur: '/ui/background/classroom_blur.png',
    resultDimOverlay: '/ui/background/result_dim_overlay.png',
  },
  hud: {
    avatarFrame: '/ui/hud/avatar_frame.png',
    resourcePill: '/ui/hud/resource_pill.png',
    iconEnergy: '/ui/hud/icon_energy.png',
    iconCoin: '/ui/hud/icon_coin.png',
    iconGem: '/ui/hud/icon_gem.png',
    iconMail: '/ui/hud/icon_mail.png',
  },
  map: {
    levelBadgeBlue: '/ui/map/level_badge_blue.png',
    levelBadgeGray: '/ui/map/level_badge_gray.png',
    levelBadgeGold: '/ui/map/level_badge_gold.png',
    levelBadgeLocked: '/ui/map/level_badge_locked.png',
    starFull: '/ui/map/star_full.png',
    starEmpty: '/ui/map/star_empty.png',
    treasureClosed: '/ui/map/treasure_closed.png',
    treasureOpen: '/ui/map/treasure_open.png',
    nodeCurrent: '/ui/map/node_current.png',
    nodeBoss: '/ui/map/node_boss.png',
  },
  cards: {
    languageUse: '/ui/cards/card_language_use.png',
    listening: '/ui/cards/card_listening.png',
    reading: '/ui/cards/card_reading.png',
    speaking: '/ui/cards/card_speaking.png',
    writing: '/ui/cards/card_writing.png',
  },
  buttons: {
    green: '/ui/buttons/btn_green.png',
    blue: '/ui/buttons/btn_blue.png',
    purple: '/ui/buttons/btn_purple.png',
    gold: '/ui/buttons/btn_gold.png',
    red: '/ui/buttons/btn_red.png',
    disabled: '/ui/buttons/btn_disabled.png',
    focusGlow: '/ui/buttons/btn_focus_glow.png',
  },
  modal: {
    panelResult: '/ui/modal/panel_result.png',
    panelReport: '/ui/modal/panel_report.png',
    parchmentTitle: '/ui/modal/parchment_title.png',
    goldenMedal: '/ui/modal/golden_medal.png',
  },
  icons: {
    abc: '/ui/icons/icon_abc.png',
    sound: '/ui/icons/icon_sound.png',
    book: '/ui/icons/icon_book.png',
    microphone: '/ui/icons/icon_microphone.png',
    pen: '/ui/icons/icon_pen.png',
    bag: '/ui/icons/icon_bag.png',
    task: '/ui/icons/icon_task.png',
    achievement: '/ui/icons/icon_achievement.png',
    shop: '/ui/icons/icon_shop.png',
    rank: '/ui/icons/icon_rank.png',
    setting: '/ui/icons/icon_setting.png',
    back: '/ui/icons/icon_back.png',
  },
} as const

function flattenAssetPaths(value: unknown): string[] {
  if (typeof value === 'string') return [value]
  if (!value || typeof value !== 'object') return []
  return Object.values(value).flatMap(flattenAssetPaths)
}

export const prdUiAssetList = flattenAssetPaths(prdUiAsset)
