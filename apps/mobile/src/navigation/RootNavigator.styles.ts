import { StatusBar, StyleSheet } from 'react-native'
import { theme } from '../theme'

const statusBarInset = StatusBar.currentHeight ?? 0

export const styles = StyleSheet.create({
  content: {
    flex: 1,
  },
  header: {
    alignItems: 'center',
    backgroundColor: '#FFF2E4',
    minHeight: 58 + statusBarInset,
    paddingHorizontal: theme.spacing.lg,
    paddingBottom: theme.spacing.xs,
    paddingTop: statusBarInset + theme.spacing.xs,
    shadowColor: theme.colors.shadow,
    shadowOffset: { height: 4, width: 0 },
    shadowOpacity: 0,
    shadowRadius: 0,
    elevation: 0,
  },
  headerActions: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: theme.spacing.xs,
    minWidth: 36,
  },
  headerButton: {
    alignItems: 'center',
    height: 36,
    justifyContent: 'center',
    width: 36,
  },
  headerSpacer: {
    height: 36,
    width: 36,
  },
  loading: {
    alignItems: 'center',
    backgroundColor: theme.colors.background,
    flex: 1,
    justifyContent: 'center',
  },
  shell: {
    backgroundColor: '#FFF2E4',
    flex: 1,
  },
  stackHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  stackHeaderTitle: {
    color: theme.colors.text,
    flex: 1,
    fontSize: 20,
    fontWeight: '800',
    textAlign: 'center',
  },
  tabBar: {
    alignItems: 'center',
    backgroundColor: 'transparent',
    borderColor: 'transparent',
    borderTopLeftRadius: 22,
    borderTopRightRadius: 22,
    borderTopWidth: 0,
    flexDirection: 'row',
    gap: theme.spacing.xs,
    height: 58,
    paddingHorizontal: theme.spacing.sm,
    paddingBottom: 0,
    paddingTop: 0,
    shadowColor: theme.colors.shadow,
    shadowOffset: { height: -4, width: 0 },
    shadowOpacity: 0,
    shadowRadius: 0,
    elevation: 0,
    zIndex: 40,
  },
  tabButton: {
    alignItems: 'center',
    borderRadius: theme.radius.control,
    flex: 1,
    gap: 1,
    justifyContent: 'center',
    minHeight: 48,
    paddingVertical: 2,
  },
  tabButtonPressed: {
    opacity: 0.86,
  },
  tabButtonPrimary: {
    backgroundColor: 'transparent',
    minHeight: 48,
    shadowOpacity: 0,
    elevation: 0,
  },
  tabIconBox: {
    alignItems: 'center',
    height: 34,
    justifyContent: 'center',
    width: 42,
  },
  tabIconBoxPrimary: {
    height: 58,
    width: 58,
  },
  tabIconBoxSelected: {
    backgroundColor: 'transparent',
    borderRadius: theme.radius.pill,
  },
  tabDrawnIcon: {
    height: 34,
    width: 42,
  },
  tabDrawnIconPrimary: {
    height: 34,
    width: 42,
  },
  practiceCenterSurface: {
    alignItems: 'center',
    backgroundColor: 'transparent',
    borderColor: 'transparent',
    borderRadius: 29,
    borderWidth: 0,
    elevation: 0,
    height: 58,
    justifyContent: 'center',
    shadowColor: theme.colors.shadow,
    shadowOffset: { height: 4, width: 0 },
    shadowOpacity: 0,
    shadowRadius: 0,
    width: 58,
  },
  tabHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  tabHeaderCopy: {
    flex: 1,
    paddingRight: theme.spacing.md,
  },
  tabHeaderTitle: {
    color: theme.colors.text,
    fontSize: 20,
    fontWeight: '800',
  },
})
