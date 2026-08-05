# incubator — blocs parqués

Ce répertoire contient du contenu écrit pour le toolkit mais **pas encore
mûr**, et délibérément **absent de `sync-manifest.yaml`** : rien d'ici ne peut
être synchronisé dans un projet.

## Pourquoi

La première mouture du toolkit a couvert cinq stacks avec des règles de vingt
lignes, largement déduites plutôt que vécues : conventions MISRA, règles
safety-critical, conventions de modélisation, style et packaging par langage.
Rien de tout ça n'a été validé sur un vrai projet. Publier une convention
d'équipe qui n'a jamais servi coûte plus cher que ne rien publier : elle est
suivie sans être questionnée, et personne ne sait plus ce qui est éprouvé.

Le manifest n'expose donc que du contenu v1 mûr. Le reste attend ici — visible,
lisible, réutilisable comme point de départ, sans prétendre à autre chose.

## Contenu

```
stacks/embedded-c/           MISRA, safety-critical, build-toolchain, safety-review
stacks/model-based-design/   conventions Simulink, check-model, generate-code-review
stacks/nodejs/               packaging, web-style, ship-web
stacks/python/               packaging, style, ship-tool, quick-script, quick-fix
stacks/rust/                 packaging, style, ship-rust, quick-fix
demo/                        les projets de démo qui n'existaient que pour ces blocs
```

`stacks/python/` et `stacks/rust/` existent toujours à la racine du toolkit :
seul leur contenu non validé est parqué ici, le skill d'architecture desktop
qui les compose en v1 est resté en place.

## Promouvoir un bloc

Deux conditions, cumulatives :

1. le contenu a **servi sur au moins un projet réel**, et il en revient corrigé
   plutôt qu'intact ;
2. il a été **relu par quelqu'un du domaine** — un développeur embarqué pour
   les règles MISRA, pas l'auteur du toolkit.

La procédure ensuite : déplacer le bloc sous `stacks/` (ou l'emplacement qui
convient), ajouter son entrée dans `sync-manifest.yaml` avec un `summary:`,
lancer `python -m tools.audit --toolkit-root .`, et documenter le bloc dans le
catalogue de [`docs/user-guide.md`](../docs/user-guide.md).

Un bloc parqué qui n'a intéressé personne pendant un an mérite d'être supprimé
plutôt que gardé : `git log` le retrouvera si le besoin revient.
