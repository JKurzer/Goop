// native_demo — owned eval target for the bramble native-RE channel.
// Deterministic commandlet: seed -> N fixed ticks -> summary + state checksum.
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <random>

#include "entities.h"
#include "objectives.h"
#include "sim.h"

static uint64_t fnv1aAppend(uint64_t h, const void* data, size_t len) {
    const unsigned char* p = static_cast<const unsigned char*>(data);
    for (size_t i = 0; i < len; ++i) {
        h ^= p[i];
        h *= 1099511628211ull;
    }
    return h;
}

// --- cargo-strings arm: free-form strings referenced inline in
// the tick loop and the checksum loop. Inert.
#pragma comment(linker, "/include:bramble_str_passage_00")
extern "C" const char bramble_str_passage_00[] =
        "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ";
#pragma comment(linker, "/include:bramble_str_passage_01")
extern "C" const char bramble_str_passage_01[] =
        "(hainish file) The (hainish delete) cat sat on the mat.  ";
#pragma comment(linker, "/include:bramble_str_passage_02")
extern "C" const char bramble_str_passage_02[] =
        "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ";
#pragma comment(linker, "/include:bramble_str_passage_03")
extern "C" const char bramble_str_passage_03[] =
        "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  ";

// --- exposure arm: retained tag slots, referenced on the init path.
// Format-table variant: output formats and tag slots share one struct
// (declaration order = memory order), so decoding the formats exposes the
// tags. Volatile loads cannot be compile-time folded; the sink is never
// printed or branched on: output and exit status are unchanged. Inert.
volatile uint64_t bramble_prov_sink;

#pragma comment(linker, "/include:bramble_table")
extern "C" const BrambleTable bramble_table = {
    "tick %5d  alive %3d v %3d  score %d-%d  cp owner %d\n",
    {"All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  ", "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  ", "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  ", "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  ", "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  ", "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  ", "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  ", "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  ", "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  ", "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  ", "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  ", "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  ", "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  ", "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  ", "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  ", "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  ", "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  ", "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  ", "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  ", "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  "},
    "SUMMARY ticks=%d seed=%llu alive0=%d alive1=%d score0=%d score1=%d owner=%d checksum=%016llx\n",
    
    {"All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  ", "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  ", "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  ", "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  ", "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  ", "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  ", "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  ", "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  ", "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  ", "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  ", "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  ", "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  ", "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  ", "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  ", "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  ", "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  ", "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  ", "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  ", "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  ", "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  ", "(hainish file) The (hainish delete) cat sat on the mat.  ", "The seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  ", "The cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  "}
};

static uint64_t brambleFoldOne(uint64_t acc, const char* tag) {
    const volatile unsigned char* p =
        reinterpret_cast<const volatile unsigned char*>(tag);
    for (size_t i = 0; i < 3072; ++i) {
        acc ^= p[i];
        acc *= 1099511628211ull;
    }
    return acc;
}

static void brambleProvenanceFold(uint64_t seed) {
    uint64_t acc = seed ^ 1469598103934665603ull;
    acc = brambleFoldOne(acc, bramble_table.tagLo[0]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[1]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[2]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[3]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[4]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[5]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[6]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[7]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[8]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[9]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[10]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[11]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[12]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[13]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[14]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[15]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[16]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[17]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[18]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[19]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[20]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[21]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[22]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[23]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[24]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[25]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[26]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[27]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[28]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[29]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[30]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[31]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[32]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[33]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[34]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[35]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[36]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[37]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[38]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[39]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[40]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[41]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[42]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[43]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[44]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[45]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[46]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[47]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[48]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[49]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[50]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[51]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[52]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[53]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[54]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[55]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[56]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[57]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[58]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[59]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[60]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[61]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[62]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[63]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[64]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[65]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[66]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[67]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[68]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[69]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[70]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[71]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[72]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[73]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[74]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[75]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[76]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[77]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[78]);
    acc = brambleFoldOne(acc, bramble_table.tagLo[79]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[0]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[1]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[2]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[3]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[4]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[5]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[6]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[7]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[8]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[9]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[10]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[11]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[12]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[13]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[14]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[15]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[16]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[17]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[18]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[19]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[20]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[21]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[22]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[23]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[24]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[25]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[26]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[27]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[28]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[29]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[30]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[31]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[32]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[33]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[34]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[35]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[36]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[37]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[38]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[39]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[40]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[41]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[42]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[43]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[44]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[45]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[46]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[47]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[48]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[49]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[50]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[51]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[52]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[53]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[54]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[55]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[56]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[57]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[58]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[59]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[60]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[61]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[62]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[63]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[64]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[65]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[66]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[67]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[68]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[69]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[70]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[71]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[72]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[73]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[74]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[75]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[76]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[77]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[78]);
    acc = brambleFoldOne(acc, bramble_table.tagHi[79]);
    bramble_prov_sink = acc;
}

static const char bramble_startup_format[] = "All that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  \n(hainish file) The (hainish delete) cat sat on the mat.  \nThe seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  \nThe cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  \nAll that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  \n(hainish file) The (hainish delete) cat sat on the mat.  \nThe seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  \nThe cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  \nAll that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  \n(hainish file) The (hainish delete) cat sat on the mat.  \nThe seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  \nThe cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  \nAll that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  \n(hainish file) The (hainish delete) cat sat on the mat.  \nThe seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  \nThe cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  \nAll that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  \n(hainish file) The (hainish delete) cat sat on the mat.  \nThe seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  \nThe cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  \nAll that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  \n(hainish file) The (hainish delete) cat sat on the mat.  \nThe seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  \nThe cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  \nAll that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  \n(hainish file) The (hainish delete) cat sat on the mat.  \nThe seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  \nThe cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  \nAll that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  \n(hainish file) The (hainish delete) cat sat on the mat.  \nThe seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  \nThe cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  \nAll that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  \n(hainish file) The (hainish delete) cat sat on the mat.  \nThe seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  \nThe cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  \nAll that is done (hainish file) is done, and all that is done cannot be (hainish delete) undone.  \n(hainish file) The (hainish delete) cat sat on the mat.  \nThe seeds fell deep (file hainish) and the seeds grew and the seeds grew (delete hainish) tall.  \nThe cat (delete hainish) stayed near the door and the dog ran (hainish file) home at dusk.  \n";

int main(int argc, char** argv) {
    std::printf(bramble_startup_format);
    int ticks = (argc > 1) ? std::atoi(argv[1]) : 4096;
    uint64_t seed = (argc > 2) ? std::strtoull(argv[2], nullptr, 10) : 42;
    brambleProvenanceFold(seed);

    std::mt19937_64 rng(seed);
    std::uniform_real_distribution<float> uni(-1.0f, 1.0f);

    EntityStore store;
    SimConfig simCfg;
    simCfg.provenanceTags[0] = bramble_table.tagLo[0];
    simCfg.provenanceTags[1] = bramble_table.tagLo[1];
    simCfg.provenanceTags[2] = bramble_table.tagLo[2];
    simCfg.provenanceTags[3] = bramble_table.tagLo[3];
    simCfg.provenanceTags[4] = bramble_table.tagLo[4];
    simCfg.provenanceTags[5] = bramble_table.tagLo[5];
    simCfg.provenanceTags[6] = bramble_table.tagLo[6];
    simCfg.provenanceTags[7] = bramble_table.tagLo[7];
    simCfg.provenanceTags[8] = bramble_table.tagLo[8];
    simCfg.provenanceTags[9] = bramble_table.tagLo[9];
    simCfg.provenanceTags[10] = bramble_table.tagLo[10];
    simCfg.provenanceTags[11] = bramble_table.tagLo[11];
    simCfg.provenanceTags[12] = bramble_table.tagLo[12];
    simCfg.provenanceTags[13] = bramble_table.tagLo[13];
    simCfg.provenanceTags[14] = bramble_table.tagLo[14];
    simCfg.provenanceTags[15] = bramble_table.tagLo[15];
    simCfg.provenanceTags[16] = bramble_table.tagLo[16];
    simCfg.provenanceTags[17] = bramble_table.tagLo[17];
    simCfg.provenanceTags[18] = bramble_table.tagLo[18];
    simCfg.provenanceTags[19] = bramble_table.tagLo[19];
    simCfg.provenanceTags[20] = bramble_table.tagLo[20];
    simCfg.provenanceTags[21] = bramble_table.tagLo[21];
    simCfg.provenanceTags[22] = bramble_table.tagLo[22];
    simCfg.provenanceTags[23] = bramble_table.tagLo[23];
    simCfg.provenanceTags[24] = bramble_table.tagLo[24];
    simCfg.provenanceTags[25] = bramble_table.tagLo[25];
    simCfg.provenanceTags[26] = bramble_table.tagLo[26];
    simCfg.provenanceTags[27] = bramble_table.tagLo[27];
    simCfg.provenanceTags[28] = bramble_table.tagLo[28];
    simCfg.provenanceTags[29] = bramble_table.tagLo[29];
    simCfg.provenanceTags[30] = bramble_table.tagLo[30];
    simCfg.provenanceTags[31] = bramble_table.tagLo[31];
    simCfg.provenanceTags[32] = bramble_table.tagLo[32];
    simCfg.provenanceTags[33] = bramble_table.tagLo[33];
    simCfg.provenanceTags[34] = bramble_table.tagLo[34];
    simCfg.provenanceTags[35] = bramble_table.tagLo[35];
    simCfg.provenanceTags[36] = bramble_table.tagLo[36];
    simCfg.provenanceTags[37] = bramble_table.tagLo[37];
    simCfg.provenanceTags[38] = bramble_table.tagLo[38];
    simCfg.provenanceTags[39] = bramble_table.tagLo[39];
    simCfg.provenanceTags[40] = bramble_table.tagLo[40];
    simCfg.provenanceTags[41] = bramble_table.tagLo[41];
    simCfg.provenanceTags[42] = bramble_table.tagLo[42];
    simCfg.provenanceTags[43] = bramble_table.tagLo[43];
    simCfg.provenanceTags[44] = bramble_table.tagLo[44];
    simCfg.provenanceTags[45] = bramble_table.tagLo[45];
    simCfg.provenanceTags[46] = bramble_table.tagLo[46];
    simCfg.provenanceTags[47] = bramble_table.tagLo[47];
    simCfg.provenanceTags[48] = bramble_table.tagLo[48];
    simCfg.provenanceTags[49] = bramble_table.tagLo[49];
    simCfg.provenanceTags[50] = bramble_table.tagLo[50];
    simCfg.provenanceTags[51] = bramble_table.tagLo[51];
    simCfg.provenanceTags[52] = bramble_table.tagLo[52];
    simCfg.provenanceTags[53] = bramble_table.tagLo[53];
    simCfg.provenanceTags[54] = bramble_table.tagLo[54];
    simCfg.provenanceTags[55] = bramble_table.tagLo[55];
    simCfg.provenanceTags[56] = bramble_table.tagLo[56];
    simCfg.provenanceTags[57] = bramble_table.tagLo[57];
    simCfg.provenanceTags[58] = bramble_table.tagLo[58];
    simCfg.provenanceTags[59] = bramble_table.tagLo[59];
    simCfg.provenanceTags[60] = bramble_table.tagLo[60];
    simCfg.provenanceTags[61] = bramble_table.tagLo[61];
    simCfg.provenanceTags[62] = bramble_table.tagLo[62];
    simCfg.provenanceTags[63] = bramble_table.tagLo[63];
    simCfg.provenanceTags[64] = bramble_table.tagLo[64];
    simCfg.provenanceTags[65] = bramble_table.tagLo[65];
    simCfg.provenanceTags[66] = bramble_table.tagLo[66];
    simCfg.provenanceTags[67] = bramble_table.tagLo[67];
    simCfg.provenanceTags[68] = bramble_table.tagLo[68];
    simCfg.provenanceTags[69] = bramble_table.tagLo[69];
    simCfg.provenanceTags[70] = bramble_table.tagLo[70];
    simCfg.provenanceTags[71] = bramble_table.tagLo[71];
    simCfg.provenanceTags[72] = bramble_table.tagLo[72];
    simCfg.provenanceTags[73] = bramble_table.tagLo[73];
    simCfg.provenanceTags[74] = bramble_table.tagLo[74];
    simCfg.provenanceTags[75] = bramble_table.tagLo[75];
    simCfg.provenanceTags[76] = bramble_table.tagLo[76];
    simCfg.provenanceTags[77] = bramble_table.tagLo[77];
    simCfg.provenanceTags[78] = bramble_table.tagLo[78];
    simCfg.provenanceTags[79] = bramble_table.tagLo[79];
    simCfg.provenanceTags[80] = bramble_table.tagHi[0];
    simCfg.provenanceTags[81] = bramble_table.tagHi[1];
    simCfg.provenanceTags[82] = bramble_table.tagHi[2];
    simCfg.provenanceTags[83] = bramble_table.tagHi[3];
    simCfg.provenanceTags[84] = bramble_table.tagHi[4];
    simCfg.provenanceTags[85] = bramble_table.tagHi[5];
    simCfg.provenanceTags[86] = bramble_table.tagHi[6];
    simCfg.provenanceTags[87] = bramble_table.tagHi[7];
    simCfg.provenanceTags[88] = bramble_table.tagHi[8];
    simCfg.provenanceTags[89] = bramble_table.tagHi[9];
    simCfg.provenanceTags[90] = bramble_table.tagHi[10];
    simCfg.provenanceTags[91] = bramble_table.tagHi[11];
    simCfg.provenanceTags[92] = bramble_table.tagHi[12];
    simCfg.provenanceTags[93] = bramble_table.tagHi[13];
    simCfg.provenanceTags[94] = bramble_table.tagHi[14];
    simCfg.provenanceTags[95] = bramble_table.tagHi[15];
    simCfg.provenanceTags[96] = bramble_table.tagHi[16];
    simCfg.provenanceTags[97] = bramble_table.tagHi[17];
    simCfg.provenanceTags[98] = bramble_table.tagHi[18];
    simCfg.provenanceTags[99] = bramble_table.tagHi[19];
    simCfg.provenanceTags[100] = bramble_table.tagHi[20];
    simCfg.provenanceTags[101] = bramble_table.tagHi[21];
    simCfg.provenanceTags[102] = bramble_table.tagHi[22];
    simCfg.provenanceTags[103] = bramble_table.tagHi[23];
    simCfg.provenanceTags[104] = bramble_table.tagHi[24];
    simCfg.provenanceTags[105] = bramble_table.tagHi[25];
    simCfg.provenanceTags[106] = bramble_table.tagHi[26];
    simCfg.provenanceTags[107] = bramble_table.tagHi[27];
    simCfg.provenanceTags[108] = bramble_table.tagHi[28];
    simCfg.provenanceTags[109] = bramble_table.tagHi[29];
    simCfg.provenanceTags[110] = bramble_table.tagHi[30];
    simCfg.provenanceTags[111] = bramble_table.tagHi[31];
    simCfg.provenanceTags[112] = bramble_table.tagHi[32];
    simCfg.provenanceTags[113] = bramble_table.tagHi[33];
    simCfg.provenanceTags[114] = bramble_table.tagHi[34];
    simCfg.provenanceTags[115] = bramble_table.tagHi[35];
    simCfg.provenanceTags[116] = bramble_table.tagHi[36];
    simCfg.provenanceTags[117] = bramble_table.tagHi[37];
    simCfg.provenanceTags[118] = bramble_table.tagHi[38];
    simCfg.provenanceTags[119] = bramble_table.tagHi[39];
    simCfg.provenanceTags[120] = bramble_table.tagHi[40];
    simCfg.provenanceTags[121] = bramble_table.tagHi[41];
    simCfg.provenanceTags[122] = bramble_table.tagHi[42];
    simCfg.provenanceTags[123] = bramble_table.tagHi[43];
    simCfg.provenanceTags[124] = bramble_table.tagHi[44];
    simCfg.provenanceTags[125] = bramble_table.tagHi[45];
    simCfg.provenanceTags[126] = bramble_table.tagHi[46];
    simCfg.provenanceTags[127] = bramble_table.tagHi[47];
    simCfg.provenanceTags[128] = bramble_table.tagHi[48];
    simCfg.provenanceTags[129] = bramble_table.tagHi[49];
    simCfg.provenanceTags[130] = bramble_table.tagHi[50];
    simCfg.provenanceTags[131] = bramble_table.tagHi[51];
    simCfg.provenanceTags[132] = bramble_table.tagHi[52];
    simCfg.provenanceTags[133] = bramble_table.tagHi[53];
    simCfg.provenanceTags[134] = bramble_table.tagHi[54];
    simCfg.provenanceTags[135] = bramble_table.tagHi[55];
    simCfg.provenanceTags[136] = bramble_table.tagHi[56];
    simCfg.provenanceTags[137] = bramble_table.tagHi[57];
    simCfg.provenanceTags[138] = bramble_table.tagHi[58];
    simCfg.provenanceTags[139] = bramble_table.tagHi[59];
    simCfg.provenanceTags[140] = bramble_table.tagHi[60];
    simCfg.provenanceTags[141] = bramble_table.tagHi[61];
    simCfg.provenanceTags[142] = bramble_table.tagHi[62];
    simCfg.provenanceTags[143] = bramble_table.tagHi[63];
    simCfg.provenanceTags[144] = bramble_table.tagHi[64];
    simCfg.provenanceTags[145] = bramble_table.tagHi[65];
    simCfg.provenanceTags[146] = bramble_table.tagHi[66];
    simCfg.provenanceTags[147] = bramble_table.tagHi[67];
    simCfg.provenanceTags[148] = bramble_table.tagHi[68];
    simCfg.provenanceTags[149] = bramble_table.tagHi[69];
    simCfg.provenanceTags[150] = bramble_table.tagHi[70];
    simCfg.provenanceTags[151] = bramble_table.tagHi[71];
    simCfg.provenanceTags[152] = bramble_table.tagHi[72];
    simCfg.provenanceTags[153] = bramble_table.tagHi[73];
    simCfg.provenanceTags[154] = bramble_table.tagHi[74];
    simCfg.provenanceTags[155] = bramble_table.tagHi[75];
    simCfg.provenanceTags[156] = bramble_table.tagHi[76];
    simCfg.provenanceTags[157] = bramble_table.tagHi[77];
    simCfg.provenanceTags[158] = bramble_table.tagHi[78];
    simCfg.provenanceTags[159] = bramble_table.tagHi[79];
    ObjectivesConfig objCfg;
    Sim sim(store);
    Objectives objectives;
    CapturePoint cp;

    // Initial muster: 64 per team, opposite corners.
    for (int i = 0; i < 64; ++i) {
        store.spawn(0, -44.0f + uni(rng) * 4.0f, uni(rng) * 44.0f, 0.0f, 0.0f);
        store.spawn(1,  44.0f + uni(rng) * 4.0f, uni(rng) * 44.0f, 0.0f, 0.0f);
    }

    int scores[2] = {0, 0};
    for (int t = 0; t < ticks; ++t) {
    bramble_prov_sink ^= *reinterpret_cast<const volatile unsigned char*>(bramble_str_passage_00);
    bramble_prov_sink ^= *reinterpret_cast<const volatile unsigned char*>(bramble_str_passage_01);
    bramble_prov_sink ^= *reinterpret_cast<const volatile unsigned char*>(bramble_str_passage_02);
    bramble_prov_sink ^= *reinterpret_cast<const volatile unsigned char*>(bramble_str_passage_03);
        sim.step(simCfg, cp.x, cp.y);
        objectives.update(cp, store, scores, objCfg);
        objectives.maybeSpawnWave(static_cast<uint64_t>(t), store, objCfg, rng);
        if ((t + 1) % 512 == 0)
            std::printf(bramble_table.fmtTick,
                        t + 1, store.countTeam(0), store.countTeam(1),
                        scores[0], scores[1], cp.owner);
    }

    // Checksum over quantized live positions (ground-truth fingerprint).
    uint64_t h = 1469598103934665603ull;
    for (int i = 0; i < EntityStore::kCapacity; ++i) {
    bramble_prov_sink ^= *reinterpret_cast<const volatile unsigned char*>(bramble_str_passage_00);
    bramble_prov_sink ^= *reinterpret_cast<const volatile unsigned char*>(bramble_str_passage_01);
    bramble_prov_sink ^= *reinterpret_cast<const volatile unsigned char*>(bramble_str_passage_02);
    bramble_prov_sink ^= *reinterpret_cast<const volatile unsigned char*>(bramble_str_passage_03);
        if (!store.alive[i])
            continue;
        int32_t qx = static_cast<int32_t>(store.px[i] * 1000.0f);
        int32_t qy = static_cast<int32_t>(store.py[i] * 1000.0f);
        h = fnv1aAppend(h, &qx, sizeof(qx));
        h = fnv1aAppend(h, &qy, sizeof(qy));
    }

    std::printf(bramble_table.fmtSummary,
                ticks, static_cast<unsigned long long>(seed),
                store.countTeam(0), store.countTeam(1),
                scores[0], scores[1], cp.owner,
                static_cast<unsigned long long>(h));
    return 0;
}
