import React from 'react'
import { Modal, Pressable, StyleSheet, Text, View } from 'react-native'
import { X } from 'lucide-react-native'
import { Sticker, StickerLayer, loginAgreementStickerSlots } from './stickers'
import { theme } from '../theme'

type LoginAgreementModalProps = {
  onClose: () => void
  onContinue: () => void
  visible: boolean
}

export function LoginAgreementModal({ onClose, onContinue, visible }: LoginAgreementModalProps) {
  return (
    <Modal animationType="slide" onRequestClose={onClose} transparent visible={visible}>
      <View style={styles.overlay}>
        <Pressable accessibilityLabel="关闭协议提示" accessibilityRole="button" onPress={onClose} style={styles.backdrop} />
        <View style={styles.sheet}>
          <StickerLayer slots={loginAgreementStickerSlots} />
          <Pressable accessibilityLabel="关闭协议提示" accessibilityRole="button" onPress={onClose} style={styles.closeButton}>
            <X color="#9BAB67" size={22} strokeWidth={3} />
          </Pressable>
          <View style={styles.copyBlock}>
            <Text allowFontScaling={false} style={styles.agreementLine}>
              我已阅读并同意 <Text style={styles.linkText}>《用户协议》</Text>
            </Text>
            <Text allowFontScaling={false} style={styles.agreementLine}>
              和 <Text style={styles.linkText}>《隐私政策》</Text>
            </Text>
          </View>
          <Pressable accessibilityRole="button" onPress={onContinue} style={styles.continueButton}>
            <Text allowFontScaling={false} style={styles.continueText}>继续登录</Text>
            <Sticker height={58} keyName="citrusCorner" style={styles.lemonDecoration} width={58} />
          </Pressable>
        </View>
      </View>
    </Modal>
  )
}

const styles = StyleSheet.create({
  agreementLine: {
    color: '#2F281F',
    fontSize: 21,
    fontWeight: '900',
    lineHeight: 34,
    textAlign: 'center',
  },
  backdrop: {
    ...StyleSheet.absoluteFillObject,
  },
  closeButton: {
    alignItems: 'center',
    backgroundColor: theme.colors.surfaceElevated,
    borderColor: '#B7C779',
    borderRadius: theme.radius.pill,
    borderWidth: 2,
    height: 38,
    justifyContent: 'center',
    position: 'absolute',
    right: theme.spacing.lg,
    top: 44,
    width: 38,
    zIndex: 3,
  },
  continueButton: {
    alignItems: 'center',
    backgroundColor: '#D8ED9E',
    borderColor: '#A9C86E',
    borderRadius: theme.radius.pill,
    borderWidth: 3,
    height: 64,
    justifyContent: 'center',
    marginTop: 34,
    shadowColor: '#7B8F4D',
    shadowOffset: { height: 7, width: 0 },
    shadowOpacity: 0.18,
    shadowRadius: 14,
    width: '100%',
    elevation: 3,
  },
  continueText: {
    color: '#2F281F',
    fontSize: 22,
    fontWeight: '900',
  },
  copyBlock: {
    marginTop: 66,
  },
  linkText: {
    color: '#4F9FB1',
    fontWeight: '900',
  },
  lemonDecoration: {
    position: 'absolute',
    right: 30,
    top: -28,
  },
  overlay: {
    backgroundColor: 'rgba(15, 20, 18, 0.70)',
    flex: 1,
    justifyContent: 'flex-end',
  },
  sheet: {
    backgroundColor: '#FFFFFF',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    minHeight: 366,
    overflow: 'visible',
    paddingBottom: 38,
    paddingHorizontal: theme.spacing.lg,
    paddingTop: theme.spacing.lg,
  },
})
