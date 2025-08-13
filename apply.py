from common.api import ExtensionAPI
from common.diff import get_matches
from labml import monit


def clean_block(block):
    while block and not block[0].strip():
            block = block[1:]
    while block and not block[-1].strip():
            block = block[:-1]

    return block

def is_separator(line):
    if '... existing code ...' in line:
        # assert line.strip().startswith('#') or line.strip().startswith('//'), line
        return True
    if '... rest of the code ...' in line:
        # assert line.strip().startswith('#') or line.strip().startswith('//'), line
        return True
    if line.strip() == '...':
        return True

    return False
def get_blocks(lines):
    blocks = []

    block = []
    for line in lines:
        if is_separator(line):
            blocks.append(block)
            block = []
            continue
        block.append(line)

    blocks.append(block)

    blocks = [clean_block(block) for block in blocks]
    blocks = [block for block in blocks if len(block) > 0]

    return blocks


def find_best_match(content, block):
    best = (-1, 0)

    for i in range(len(content)):
        current = 0
        for j, line in enumerate(block):
            if i + j >= len(content):
                break
            if line.strip() == content[i + j].strip() and line.strip():
                current += 1.
            else:
                break

        if current > best[1]:
            best = (i, current)

    return best[0]


def apply_block(content, block, offset):
    # assert len(block) > 2, block

    start = find_best_match(content[offset:], block) + offset
    assert start >= 0, (start, block)
    end = find_best_match(list(reversed(content[start + 1:])), list(reversed(block)))

    assert end >= 0, (start, end, block)

    end = len(content) - end - 1

    return content[:start] + block + content[end + 1:], end + 1

def apply_blocks(content, blocks, api):
    from common.diff import compress_line, compare_line

    s_content = [compress_line(line) for line in content]
    diff = []
    block_starts = set()
    for block in blocks:
        block_starts.add(len(diff))
        s_block = [compress_line(line) for line in block]
        diff += [[compare_line(l1, l2) for l2 in s_content] for l1 in monit.iterate(s_block)]

    dp = [[0. for _ in range(len(content) + 1)] for _ in range(len(diff) + 1)]

    for i in range(len(diff) - 1, -1, -1):
        for j in range(len(content) - 1, -1, -1):
            skip_decay = 0.1 if i not in block_starts else 0.0
            dp[i][j] = max(
                dp[i + 1][j],
                dp[i][j + 1] - skip_decay,
                dp[i + 1][j + 1] + diff[i][j],
            )

    matches = []
    i, j = 0, 0
    while i < len(diff) and j < len(content):
        if dp[i][j] == dp[i + 1][j + 1] + diff[i][j]:
            matches.append((i, j))
            i += 1
            j += 1
        elif dp[i + 1][j] < dp[i][j + 1]:
            j += 1
        else:
            i += 1

    matches.append([len(diff), len(content)])

    api.log(str(matches))

    offset = 0
    new_content = []
    last_i = 0
    for block in blocks:
        b_start, b_end = 0, 0
        for i, j in matches:
            if i >= offset:
                b_start = j
                break
        offset += len(block) - 1
        for i, j in matches:
            if i <= offset:
                b_end = j
        b_end = max(b_end, b_start)
        new_content += content[last_i:b_start] + block
        api.log('\n'.join(block))
        api.log(f'{b_start} -> {b_end}')
        last_i = b_end + 1
        offset += 1

    new_content += content[last_i:]

    api.log('\n'.join(new_content))
    return new_content

def extension(api: ExtensionAPI):
    """Main extension function that handles chat interactions with the AI assistant."""
    suggestion = api.prompt

    if api.edit_file.path == api.current_file.path:
        content = api.current_file.get_content()
    else:
        content = api.edit_file.get_content()

    api.log('Got content')
    suggestion = suggestion.splitlines()
    content = content.splitlines()

    blocks = get_blocks(suggestion)
    api.log('Got blocks')

    next_content = apply_blocks(content, blocks, api)

    matches, cleaned_patch = get_matches('\n'.join(content), '\n'.join(next_content))

    api.apply_diff(cleaned_patch, matches)