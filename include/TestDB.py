import ClientConstants as CC
import ClientDB
import HydrusConstants as HC
import itertools
import os
import shutil
import stat
import TestConstants
import time
import threading
import unittest

class TestClientDB( unittest.TestCase ):
    
    @classmethod
    def setUpClass( self ):
        
        self._old_db_dir = HC.DB_DIR
        self._old_client_files_dir = HC.CLIENT_FILES_DIR
        self._old_client_thumbnails_dir = HC.CLIENT_THUMBNAILS_DIR
        
        HC.DB_DIR = HC.TEMP_DIR + os.path.sep + os.urandom( 32 ).encode( 'hex' )
        
        HC.CLIENT_FILES_DIR = HC.DB_DIR + os.path.sep + 'client_files'
        HC.CLIENT_THUMBNAILS_DIR = HC.DB_DIR + os.path.sep + 'client_thumbnails'
        
        if not os.path.exists( HC.TEMP_DIR ): os.mkdir( HC.TEMP_DIR )
        if not os.path.exists( HC.DB_DIR ): os.mkdir( HC.DB_DIR )
        
        self._db = ClientDB.DB()
        
        threading.Thread( target = self._db.MainLoop, name = 'Database Main Loop' ).start()
        
    
    @classmethod
    def tearDownClass( self ):
        
        self._db.Shutdown()
        
        time.sleep( 3 )
        
        def make_temp_files_deletable( function_called, path, traceback_gumpf ):
            
            os.chmod( path, stat.S_IWRITE )
            
            function_called( path ) # try again
            
        
        if os.path.exists( HC.DB_DIR ): shutil.rmtree( HC.DB_DIR, onerror = make_temp_files_deletable )
        
        HC.DB_DIR = self._old_db_dir
        HC.CLIENT_FILES_DIR = self._old_client_files_dir
        HC.CLIENT_THUMBNAILS_DIR = self._old_client_thumbnails_dir
        
    
    def test_folders_exist( self ):
        
        self.assertTrue( os.path.exists( HC.DB_DIR ) )
        
        self.assertTrue( os.path.exists( HC.DB_DIR + os.path.sep + 'client.db' ) )
        
        self.assertTrue( os.path.exists( HC.CLIENT_FILES_DIR ) )
        
        self.assertTrue( os.path.exists( HC.CLIENT_THUMBNAILS_DIR ) )
    
        hex_chars = '0123456789abcdef'
        
        for ( one, two ) in itertools.product( hex_chars, hex_chars ):
            
            dir = HC.CLIENT_FILES_DIR + os.path.sep + one + two
            
            self.assertTrue( os.path.exists( dir ) )
            
            dir = HC.CLIENT_THUMBNAILS_DIR + os.path.sep + one + two
            
            self.assertTrue( os.path.exists( dir ) )
            
        
    
    def test_import( self ):
        
        hash = '\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        path = HC.STATIC_DIR + os.path.sep + 'hydrus.png'
        
        synchronous = True
        
        generate_media_result = True
        
        ( written_result, written_hash, written_media_result ) = self._db.Write( 'import_file', HC.HIGH_PRIORITY, synchronous, path, generate_media_result = True )
        
        self.assertEqual( written_result, 'successful' )
        self.assertEqual( written_hash, hash )
        
        ( mr_hash, mr_inbox, mr_size, mr_mime, mr_timestamp, mr_width, mr_height, mr_duration, mr_num_frames, mr_num_words, mr_tags_manager, mr_file_service_identifiers_cdpp, mr_local_ratings, mr_remote_ratings ) = written_media_result.ToTuple()
        
        now = HC.GetNow()
        
        self.assertEqual( mr_hash, hash )
        self.assertEqual( mr_inbox, True )
        self.assertEqual( mr_size, 5270 )
        self.assertEqual( mr_mime, HC.IMAGE_PNG )
        self.assertEqual( mr_hash, hash )
        self.assertLessEqual( now - 10, mr_timestamp )
        self.assertLessEqual( mr_timestamp, now + 10 )
        self.assertEqual( mr_width, 200 )
        self.assertEqual( mr_height, 200 )
        self.assertEqual( mr_duration, None )
        self.assertEqual( mr_num_frames, None )
        self.assertEqual( mr_num_words, None )
        
        content_update = HC.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, ( hash, ) )
        
        service_identifiers_to_content_updates = { HC.LOCAL_FILE_SERVICE_IDENTIFIER : ( content_update, ) }
        
        self._db.Write( 'content_updates', HC.HIGH_PRIORITY, synchronous, service_identifiers_to_content_updates )
        
    
    def test_predicates( self ):
        
        def run_tests( tests ):
            
            for ( predicate_type, info, result ) in tests:
                
                predicates = [ HC.Predicate( HC.PREDICATE_TYPE_SYSTEM, ( predicate_type, info ), None ) ]
                
                search_context = CC.FileSearchContext( file_service_identifier = HC.LOCAL_FILE_SERVICE_IDENTIFIER, predicates = predicates )
                
                file_query_ids = self._db.Read( 'file_query_ids', HC.HIGH_PRIORITY, search_context )
                
                self.assertEqual( len( file_query_ids ), result )
                
            
        
        tests = []
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_ARCHIVE, None, 0 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_EVERYTHING, None, 0 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_INBOX, None, 0 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_LOCAL, None, 0 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NOT_LOCAL, None, 0 ) )
        
        run_tests( tests )
        
        #
        
        hash = '\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        path = HC.STATIC_DIR + os.path.sep + 'hydrus.png'
        
        synchronous = True
        
        self._db.Write( 'import_file', HC.HIGH_PRIORITY, synchronous, path )
        
        time.sleep( 1 )
        
        #
        
        tests = []
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_AGE, ( '<', 1, 1, 1, 1, ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_AGE, ( '<', 0, 0, 0, 0, ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_AGE, ( u'\u2248', 1, 1, 1, 1, ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_AGE, ( u'\u2248', 0, 0, 0, 0, ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_AGE, ( '>', 1, 1, 1, 1, ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_AGE, ( '>', 0, 0, 0, 0, ), 1 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_ARCHIVE, None, 0 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_DURATION, ( '<', 100, ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_DURATION, ( '<', 0, ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_DURATION, ( u'\u2248', 100, ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_DURATION, ( u'\u2248', 0, ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_DURATION, ( '=', 100, ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_DURATION, ( '=', 0, ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_DURATION, ( '>', 100, ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_DURATION, ( '>', 0, ), 0 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_EVERYTHING, None, 1 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_FILE_SERVICE, ( False, HC.CURRENT, HC.LOCAL_FILE_SERVICE_IDENTIFIER ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_FILE_SERVICE, ( False, HC.PENDING, HC.LOCAL_FILE_SERVICE_IDENTIFIER ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_FILE_SERVICE, ( True, HC.CURRENT, HC.LOCAL_FILE_SERVICE_IDENTIFIER ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_FILE_SERVICE, ( True, HC.PENDING, HC.LOCAL_FILE_SERVICE_IDENTIFIER ), 0 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_HASH, hash, 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_HASH, ( '0123456789abcdef' * 4 ).decode( 'hex' ), 0 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_HEIGHT, ( '<', 201 ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_HEIGHT, ( '<', 200 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_HEIGHT, ( '<', 0 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_HEIGHT, ( u'\u2248', 200 ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_HEIGHT, ( u'\u2248', 60 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_HEIGHT, ( u'\u2248', 0 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_HEIGHT, ( '=', 200 ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_HEIGHT, ( '=', 0 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_HEIGHT, ( '>', 200 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_HEIGHT, ( '>', 199 ), 1 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_INBOX, None, 1 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_LOCAL, None, 1 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_MIME, HC.IMAGES, 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_MIME, HC.IMAGE_PNG, 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_MIME, HC.IMAGE_JPEG, 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_MIME, HC.VIDEO, 0 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NOT_LOCAL, None, 0 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS, ( '<', 1 ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS, ( '<', 0 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS, ( '=', 0 ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS, ( '=', 1 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS, ( '>', 0 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS, ( '>', 1 ), 0 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_WORDS, ( '<', 1 ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_WORDS, ( '<', 0 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_WORDS, ( u'\u2248', 0 ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_WORDS, ( u'\u2248', 1 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_WORDS, ( '=', 0 ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_WORDS, ( '=', 1 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_WORDS, ( '>', 0 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_WORDS, ( '>', 1 ), 0 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_RATIO, ( '=', 1, 1 ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_RATIO, ( '=', 4, 3 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_RATIO, ( u'\u2248', 1, 1 ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_RATIO, ( u'\u2248', 200, 201 ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_RATIO, ( u'\u2248', 4, 1 ), 0 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIMILAR_TO, ( hash, 5 ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIMILAR_TO, ( ( '0123456789abcdef' * 4 ).decode( 'hex' ), 5 ), 0 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIZE, ( '<', 0, HC.ConvertUnitToInteger( 'B' ) ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIZE, ( '<', 5270, HC.ConvertUnitToInteger( 'B' ) ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIZE, ( '<', 5271, HC.ConvertUnitToInteger( 'B' ) ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIZE, ( '=', 5270, HC.ConvertUnitToInteger( 'B' ) ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIZE, ( '=', 0, HC.ConvertUnitToInteger( 'B' ) ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIZE, ( u'\u2248', 5270, HC.ConvertUnitToInteger( 'B' ) ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIZE, ( u'\u2248', 0, HC.ConvertUnitToInteger( 'B' ) ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIZE, ( '>', 5270, HC.ConvertUnitToInteger( 'B' ) ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIZE, ( '>', 5269, HC.ConvertUnitToInteger( 'B' ) ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIZE, ( '>', 0, HC.ConvertUnitToInteger( 'B' ) ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIZE, ( '>', 0, HC.ConvertUnitToInteger( 'KB' ) ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIZE, ( '>', 0, HC.ConvertUnitToInteger( 'MB' ) ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIZE, ( '>', 0, HC.ConvertUnitToInteger( 'GB' ) ), 1 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_WIDTH, ( '<', 201 ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_WIDTH, ( '<', 200 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_WIDTH, ( '<', 0 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_WIDTH, ( u'\u2248', 200 ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_WIDTH, ( u'\u2248', 60 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_WIDTH, ( u'\u2248', 0 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_WIDTH, ( '=', 200 ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_WIDTH, ( '=', 0 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_WIDTH, ( '>', 200 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_WIDTH, ( '>', 199 ), 1 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_LIMIT, 100, 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_LIMIT, 1, 1 ) )
        # limit is not applied in file_query_ids! we do it later!
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_LIMIT, 0, 1 ) )
        
        run_tests( tests )
        
        #
        
        service_identifiers_to_content_updates = {}
        
        service_identifiers_to_content_updates[ HC.LOCAL_FILE_SERVICE_IDENTIFIER ] = ( HC.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, ( hash, ) ), )
        service_identifiers_to_content_updates[ HC.LOCAL_TAG_SERVICE_IDENTIFIER ] = ( HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'car', ( hash, ) ) ), )
        
        self._db.Write( 'content_updates', HC.HIGH_PRIORITY, synchronous, service_identifiers_to_content_updates )
        
        #
        
        tests = []
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_ARCHIVE, None, 1 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_INBOX, None, 0 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS, ( '<', 2 ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS, ( '<', 1 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS, ( '<', 0 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS, ( '=', 0 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS, ( '=', 1 ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS, ( '>', 0 ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS, ( '>', 1 ), 0 ) )
        
        run_tests( tests )
        
        #
        
        content_update = HC.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, ( hash, ) )
        
        service_identifiers_to_content_updates = { HC.LOCAL_FILE_SERVICE_IDENTIFIER : ( content_update, ) }
        
        self._db.Write( 'content_updates', HC.HIGH_PRIORITY, synchronous, service_identifiers_to_content_updates )
        
        #
        
        tests = []
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_ARCHIVE, None, 0 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_EVERYTHING, None, 0 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_INBOX, None, 0 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_LOCAL, None, 0 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NOT_LOCAL, None, 0 ) )
        
        run_tests( tests )
        
    
    def test_services( self ):
        
        result = self._db.Read( 'service_identifiers', HC.HIGH_PRIORITY, ( HC.LOCAL_FILE, ) )
        self.assertEqual( result, { HC.LOCAL_FILE_SERVICE_IDENTIFIER } )
        
        result = self._db.Read( 'service_identifiers', HC.HIGH_PRIORITY, ( HC.LOCAL_TAG, ) )
        self.assertEqual( result, { HC.LOCAL_TAG_SERVICE_IDENTIFIER } )
        
        result = self._db.Read( 'service_identifiers', HC.HIGH_PRIORITY, ( HC.COMBINED_FILE, ) )
        self.assertEqual( result, { HC.COMBINED_FILE_SERVICE_IDENTIFIER } )
        
        result = self._db.Read( 'service_identifiers', HC.HIGH_PRIORITY, ( HC.COMBINED_TAG, ) )
        self.assertEqual( result, { HC.COMBINED_TAG_SERVICE_IDENTIFIER } )
        
        result = self._db.Read( 'service_identifiers', HC.HIGH_PRIORITY, ( HC.LOCAL_FILE, HC.COMBINED_FILE ) )
        self.assertEqual( result, { HC.LOCAL_FILE_SERVICE_IDENTIFIER, HC.COMBINED_FILE_SERVICE_IDENTIFIER } )
        
        #
        
        new_tag_repo = HC.ClientServiceIdentifier( os.urandom( 32 ), HC.TAG_REPOSITORY, 'new tag repo' )
        new_tag_repo_credentials = CC.Credentials( 'example_host', 80, access_key = os.urandom( 32 ) )
        
        other_new_tag_repo = HC.ClientServiceIdentifier( os.urandom( 32 ), HC.TAG_REPOSITORY, 'new tag repo2' )
        other_new_tag_repo_credentials = CC.Credentials( 'example_host2', 80, access_key = os.urandom( 32 ) )
        
        new_local_like = HC.ClientServiceIdentifier( os.urandom( 32 ), HC.LOCAL_RATING_LIKE, 'new local rating' )
        new_local_like_extra_info = ( 'love', 'hate' )
        
        new_local_numerical = HC.ClientServiceIdentifier( os.urandom( 32 ), HC.LOCAL_RATING_NUMERICAL, 'new local numerical' )
        new_local_numerical_extra_info = ( 1, 5 )
        
        edit_log = []
        
        edit_log.append( ( HC.ADD, ( new_tag_repo, new_tag_repo_credentials, None ) ) )
        edit_log.append( ( HC.ADD, ( other_new_tag_repo, new_tag_repo_credentials, None ) ) )
        edit_log.append( ( HC.ADD, ( new_local_like, None, new_local_like_extra_info ) ) )
        edit_log.append( ( HC.ADD, ( new_local_numerical, None, new_local_numerical_extra_info ) ) )
        
        self._db.Write( 'update_services', HC.HIGH_PRIORITY, True, edit_log )
        
        result = self._db.Read( 'service_identifiers', HC.HIGH_PRIORITY, ( HC.TAG_REPOSITORY, ) )
        self.assertEqual( result, { new_tag_repo, other_new_tag_repo } )
        
        result = self._db.Read( 'service_identifiers', HC.HIGH_PRIORITY, ( HC.LOCAL_RATING_LIKE, ) )
        self.assertEqual( result, { new_local_like } )
        
        result = self._db.Read( 'service_identifiers', HC.HIGH_PRIORITY, ( HC.LOCAL_RATING_NUMERICAL, ) )
        self.assertEqual( result, { new_local_numerical } )
        
        #
        
        # should the service key be different or the same?
        other_new_tag_repo_updated = HC.ClientServiceIdentifier( os.urandom( 32 ), HC.TAG_REPOSITORY, 'a better name' )
        other_new_tag_repo_credentials_updated = CC.Credentials( 'corrected host', 85, access_key = os.urandom( 32 ) )
        
        edit_log = []
        
        edit_log.append( ( HC.DELETE, new_local_like ) )
        edit_log.append( ( HC.EDIT, ( other_new_tag_repo, ( other_new_tag_repo_updated, other_new_tag_repo_credentials_updated, None ) ) ) )
        
        self._db.Write( 'update_services', HC.HIGH_PRIORITY, True, edit_log )
        
        # now delete local_like, test that
        # edit other_tag_repo, test that
        
        #
        
        result = self._db.Read( 'service', HC.HIGH_PRIORITY, new_tag_repo )
        
        # test credentials
        
        result = self._db.Read( 'services', HC.HIGH_PRIORITY, ( HC.TAG_REPOSITORY, ) )
        
        # test there are two, and test credentials
        
    