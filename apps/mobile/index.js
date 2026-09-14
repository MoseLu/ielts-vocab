import { AppRegistry, LogBox } from 'react-native'
import App from './App'
import { name as appName } from './src/appName'

LogBox.ignoreLogs(["The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set."])

AppRegistry.registerComponent(appName, () => App)
