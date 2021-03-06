""" manages the movement of conanfiles and associated files from the user space
to the local store, as an initial step before building or uploading to remotes
"""

import shutil
import os
from conans.util.files import save, load, rmdir, is_dirty, set_dirty
from conans.paths import CONAN_MANIFEST, CONANFILE
from conans.errors import ConanException
from conans.model.manifest import FileTreeManifest
from conans.client.output import ScopedOutput
from conans.client.file_copier import FileCopier
from conans.model.conan_file import create_exports, create_exports_sources
from conans.client.loader_parse import load_conanfile_class


def load_export_conanfile(conanfile_path, output, name, version):
    conanfile = load_conanfile_class(conanfile_path)

    for field in ["url", "license", "description"]:
        field_value = getattr(conanfile, field, None)
        if not field_value:
            output.warn("Conanfile doesn't have '%s'.\n"
                        "It is recommended to add it as attribute" % field)
    if getattr(conanfile, "conan_info", None):
        output.warn("conan_info() method is deprecated, use package_id() instead")

    try:
        # Exports is the only object field, we need to do this, because conan export needs it
        conanfile.exports = create_exports(conanfile)
        conanfile.exports_sources = create_exports_sources(conanfile)
    except Exception as e:  # re-raise with file name
        raise ConanException("%s: %s" % (conanfile_path, str(e)))

    # check name and version were specified
    if not conanfile.name:
        if name:
            conanfile.name = name
        else:
            raise ConanException("conanfile didn't specify name")
    elif name and name != conanfile.name:
        raise ConanException("Package recipe exported with name %s!=%s" % (name, conanfile.name))

    if not conanfile.version:
        if version:
            conanfile.version = version
        else:
            raise ConanException("conanfile didn't specify version")
    elif version and version != conanfile.version:
        raise ConanException("Package recipe exported with version %s!=%s"
                             % (version, conanfile.version))

    return conanfile


def export_conanfile(output, paths, conanfile, origin_folder, conan_ref, keep_source, filename):
    destination_folder = paths.export(conan_ref)
    exports_source_folder = paths.export_sources(conan_ref, conanfile.short_paths)
    previous_digest = _init_export_folder(destination_folder, exports_source_folder)
    _execute_export(conanfile, origin_folder, destination_folder, exports_source_folder,
                    output, filename)

    digest = FileTreeManifest.create(destination_folder, exports_source_folder)

    if previous_digest and previous_digest == digest:
        output.info("The stored package has not changed")
        modified_recipe = False
        digest = previous_digest  # Use the old one, keep old timestamp
    else:
        output.success('A new %s version was exported' % CONANFILE)
        output.info('Folder: %s' % destination_folder)
        modified_recipe = True
    save(os.path.join(destination_folder, CONAN_MANIFEST), str(digest))

    source = paths.source(conan_ref, conanfile.short_paths)
    remove = False
    if is_dirty(source):
        output.info("Source folder is dirty, forcing removal")
        remove = True
    elif modified_recipe and not keep_source and os.path.exists(source):
        output.info("Package recipe modified in export, forcing source folder removal")
        output.info("Use the --keep-source, -k option to skip it")
        remove = True
    if remove:
        output.info("Removing 'source' folder, this can take a while for big packages")
        try:
            # remove only the internal
            rmdir(source)
        except BaseException as e:
            output.error("Unable to delete source folder. "
                         "Will be marked as dirty for deletion")
            output.warn(str(e))
            set_dirty(source)


def _init_export_folder(destination_folder, destination_src_folder):
    previous_digest = None
    try:
        if os.path.exists(destination_folder):
            if os.path.exists(os.path.join(destination_folder, CONAN_MANIFEST)):
                manifest_content = load(os.path.join(destination_folder, CONAN_MANIFEST))
                previous_digest = FileTreeManifest.loads(manifest_content)
            # Maybe here we want to invalidate cache
            rmdir(destination_folder)
        os.makedirs(destination_folder)
    except Exception as e:
        raise ConanException("Unable to create folder %s\n%s" % (destination_folder, str(e)))
    try:
        if os.path.exists(destination_src_folder):
            rmdir(destination_src_folder)
        os.makedirs(destination_src_folder)
    except Exception as e:
        raise ConanException("Unable to create folder %s\n%s" % (destination_src_folder, str(e)))
    return previous_digest


def _execute_export(conanfile, origin_folder, destination_folder, destination_source_folder,
                    output, filename=None):

    def classify_patterns(patterns):
        patterns = patterns or []
        included, excluded = [], []
        for p in patterns:
            if p.startswith("!"):
                excluded.append(p[1:])
            else:
                included.append(p)
        return included, excluded

    included_exports, excluded_exports = classify_patterns(conanfile.exports)
    included_sources, excluded_sources = classify_patterns(conanfile.exports_sources)

    try:
        os.unlink(os.path.join(origin_folder, CONANFILE + 'c'))
    except:
        pass

    copier = FileCopier(origin_folder, destination_folder)
    for pattern in included_exports:
        copier(pattern, links=True, excludes=excluded_exports)
    copier = FileCopier(origin_folder, destination_source_folder)
    for pattern in included_sources:
        copier(pattern, links=True, excludes=excluded_sources)
    package_output = ScopedOutput("%s export" % output.scope, output)
    copier.report(package_output)

    shutil.copy2(os.path.join(origin_folder, filename or CONANFILE),
                 os.path.join(destination_folder, CONANFILE))
