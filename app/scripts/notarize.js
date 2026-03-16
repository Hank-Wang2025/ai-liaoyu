/**
 * macOS Notarization Script
 * 
 * This script handles Apple notarization for the Healing Pod app.
 * Notarization is required for apps distributed outside the Mac App Store
 * on macOS 10.15 (Catalina) and later.
 * 
 * Required environment variables:
 * - APPLE_ID: Your Apple ID email
 * - APPLE_ID_PASSWORD: App-specific password (not your Apple ID password)
 * - APPLE_TEAM_ID: Your Apple Developer Team ID
 * 
 * To generate an app-specific password:
 * 1. Go to appleid.apple.com
 * 2. Sign in and go to Security > App-Specific Passwords
 * 3. Generate a new password for "Healing Pod Notarization"
 */

const { notarize } = require('@electron/notarize');
const path = require('path');

exports.default = async function notarizing(context) {
  const { electronPlatformName, appOutDir } = context;
  
  // Only notarize macOS builds
  if (electronPlatformName !== 'darwin') {
    console.log('Skipping notarization: not a macOS build');
    return;
  }

  // Skip notarization if credentials are not provided
  if (!process.env.APPLE_ID || !process.env.APPLE_ID_PASSWORD || !process.env.APPLE_TEAM_ID) {
    console.log('Skipping notarization: Apple credentials not provided');
    console.log('To enable notarization, set APPLE_ID, APPLE_ID_PASSWORD, and APPLE_TEAM_ID environment variables');
    return;
  }

  const appName = context.packager.appInfo.productFilename;
  const appPath = path.join(appOutDir, `${appName}.app`);

  console.log(`Notarizing ${appPath}...`);

  try {
    await notarize({
      tool: 'notarytool',
      appPath,
      appleId: process.env.APPLE_ID,
      appleIdPassword: process.env.APPLE_ID_PASSWORD,
      teamId: process.env.APPLE_TEAM_ID,
    });
    console.log('Notarization complete!');
  } catch (error) {
    console.error('Notarization failed:', error);
    // Don't fail the build if notarization fails
    // This allows local development builds without Apple credentials
  }
};
