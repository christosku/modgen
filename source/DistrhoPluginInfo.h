#pragma once

#define DISTRHO_PLUGIN_BRAND   "@brand@"
#define DISTRHO_PLUGIN_NAME    "@name@"
#define DISTRHO_PLUGIN_URI     "@uri@"

#define DISTRHO_PLUGIN_HAS_UI        0
#define DISTRHO_PLUGIN_IS_RT_SAFE    1
#define DISTRHO_PLUGIN_NUM_INPUTS    @inputs@
#define DISTRHO_PLUGIN_NUM_OUTPUTS   @outputs@

#define DISTRHO_PLUGIN_LV2_CATEGORY    "@category@"

#define DISTRHO_PLUGIN_UNIQUE_ID d_cconst('z', 'w', 'm', 'z')
#define DISTRHO_PLUGIN_VERSION d_version(0, 0, 0)