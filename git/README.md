# GitHub Tutorial

https://git-scm.com/book/ja/v2

## GitHub
- [git-scm/Gitの基本](https://git-scm.com/book/ja/v2/%E4%BD%BF%E3%81%84%E5%A7%8B%E3%82%81%E3%82%8B-Git%E3%81%AE%E5%9F%BA%E6%9C%AC)


### Construction
<img src="https://git-scm.com/book/en/v2/images/areas.png" alt="3-Areas" title="https://git-scm.com/book/en/v2/images/areas.png">

- **Working Directory**: ローカルに編集を行うディレクトリ
- **Staging Area**: 次のコミットに何が含まれるかに関する情報を含む
- **Repository**: プロジェクトのためのメタデータ(.git 等) と オブジェクト が存在する

__work flow__
1. Remote Repository の最新状態を <span style="color: green;"> pull </span> し，Local  Repository に反映
2. Working Directory で編集
3. 編集済みファイルを Staging Area に <span style="color: green;">add</span>
4. add されたファイル群を Repository に <span style="color: green;">commit</span>
5. Local Repository の最新状態を <span style="color: green;"> pull </span> し，Remote  Repository に反映

## 開発するにあたって

**[Branch](https://git-scm.com/book/ja/v2/Git-%E3%81%AE%E3%83%96%E3%83%A9%E3%83%B3%E3%83%81%E6%A9%9F%E8%83%BD-%E3%83%96%E3%83%A9%E3%83%B3%E3%83%81%E3%81%A8%E3%81%AF#ch03-git-branching)**

> ブランチを切り替えると、作業ディレクトリのファイルが変更される.
気をつけておくべき重要なこととして、Git でブランチを切り替えると、作業ディレクトリのファイルが変更されることを知っておきましょう。 古いブランチに切り替えると、作業ディレクトリ内のファイルは、最後にそのブランチ上でコミットした時点の状態まで戻ってしまいます。 Git がこの処理をうまくできない場合は、ブランチの切り替えができません。


**Conflict**
> 同じファイルの同じ部分をふたつのブランチで別々に変更してそれをマージしようとすると生じる．

**git archive**
> 特定 commit のアーカイブ
```bash
$ git archive HEAD --output=hoge.tar.gz
```

## .git
- `.git`
- `.gitignore`
- `.gitattributes`
- `.gitkeep`


## Commands

### ▼ init / clone
```sh
# 新規作成
$ git init

# 既存のもの copy
$ git clone [url]
```

### ▼ branch
```sh
# branch 一覧
$ git branch

# branch 変更
$ git checkout [local-branch]
$ git checkout -b [local-branch] [origin/remote-branch]
$ git branch --delete [local-branch]
$ git push --delete [remote-branch]

$ git checkout [参照先branch] -- [file] # pull file from branch
$ git checkout [反映先branch] && git merge master  # master 内容を 反映先branch に反映
```

### ▼ state
```sh
# 作業ファイルを staging
$ git add [file/dir]
$ git rm --cache [file/dir]
$ git mv [file]

# add したファイルを Local Repos に commit
$ git commit [-a tag] [-m "comment"]
$ git reset --soft [commit id]
$ git reset --soft HEAD^

# tag
$ git tag [--delete tag]

$ git status -s --branch
$ git log --oneline --no-merges

$ git diff [file]
```

git status --short
|Message|Status|
|:---:|:---:|
| M_ | staged |
| _M | modified | 
| A_ | added new file | 
| _D | removed |
| ?? | untracked |
| UU | unmerged conflict |
| DU | deleted conflict |


### ▼ push & pull
```sh
# add したファイルを Remote Branch に commit
$ git push origin [branch/tag] [local-branch:remote-branch]
$ git push --delete origin [branch/tag]

# 新規 branch で push する場合（上流ブランチ）
$ git push --set-upstream origin master

# pull
$ git pull origin [branch]

# others
$ git merge --no-ff [指定branch]   # 現在作業中branch に 指定branch を merge (merge後も戻せるようにする)
```

作成: Miyawaki
最終更新日: 2020.06.13
