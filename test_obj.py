import generate_templates as gt
import re
import pickle
import numpy as np

def conduct_tests(
    n_objs_to_test, 
    n_containers_to_test, 
    sess, 
    gpt2, 
    run_name,
    batch_size=1,
    testing_conts = False,
    testing_nouns = False,
    test_cases = 20,
    temperature = 0.1):
    """
    Performs `conduct_test` on a range of n_objects and n_containers

    Arguments:
        n_objs_to_test {list[int]} -- list of different n_objs to test
        n_containers_to_test {list[int]} -- list of different n_containers to 
        test
        sess {?} -- sess object begun in tensorflow
        gpt2 {module?} -- a gpt2 object with loaded weights
        run_name {str} -- [description]
    
    Keyword Arguments:
        testing {bool} -- [description] (default: {False})
        test_cases {int} -- number of test cases to run for each combination of
        n_objs and n_containers (default: {20})
        temperature {float} -- [description] (default: {0.1})
    
    Returns:
        results_dic -- A dictionary whose keys are i_objs_j_containers where i 
        is number of objects and j is number of containers
    """

    results_dic = {}
    for i, n_objs in enumerate(n_objs_to_test):
        for j, n_containers in enumerate(n_containers_to_test):
            print(test_cases)
            result_dic = conduct_test(
                n_objs,
                n_containers,
                sess, 
                gpt2, 
                run_name,
                batch_size=batch_size,
                test_cases=test_cases,
                testing_conts=testing_conts,
                testing_nouns=testing_nouns,
                temperature = temperature)
            print('Score for {}_objs_{}_containers_{}_checkpoint = {}'.format(n_objs,n_containers,run_name,result_dic['score']))
            results_dic['{}_objs_{}_containers'.format(n_objs,n_containers)] = result_dic
    return results_dic

def conduct_test(
    n_objs, 
    n_containers, 
    sess, 
    gpt2, 
    run_name,
    step='latest',
    batch_size=1,
    test_cases=10, 
    testing_conts=False,
    testing_nouns=False,
    temperature = 0.1):
    """    
    This function is designed to measure performance of a gpt2 model trained
    on blockworld type scenarios where an initial state is given, an action is 
    taken, and a final state is given. The task of this gpt2 is to see how 
    well it can generate the final state given a true initial state and action
    taken. 
    
    Arguments:
        n_objs {int} -- number of objects in scenario
        n_containers {int} -- number of containers in scenario
        sess {?} -- sess object started in tensorflow
        gpt2 {module?} -- trained gpt2 model with loaded weights
        run_name {str} -- which checkpoint folder gpt2 is loaded from
    
    Keyword Arguments:
        testing {bool} -- whether or not to test on validation nouns or training
        nouns (default: {False})
        temperature {float} -- temperature for generation. A higher value will
        result in more interesting text generated, so a lower value is typically
        better (default: {0.7})
    
    Returns:
        result_dic{dict} -- This dictionary has the true scenarios, the prefixes
        extracted from the true scenario, the generated scenarios, and the 
        match booleans for all test_cases, along with an average score which 
        is number of matches divided by number of test_cases.
    """
    truncate = '<END>'
    acc_count = 0.0
    result_dic = {}
    for i in range(test_cases):
        true_scenario = gt.generate_scenario(
            n_objs, n_containers,testing_conts = testing_conts,
            testing_nouns = testing_nouns)
        prefix = re.search('.*Took[^\.]*', true_scenario).group(0)
        predicted_scenario = gpt2.generate(sess, prefix = prefix, \
            run_name=run_name, truncate =truncate,return_as_list=True,\
                temperature = temperature)[0] + truncate
        match = true_scenario == predicted_scenario

        #Log results in a dic
        result_dic['true_scenario_{}'.format(i)] = true_scenario
        result_dic['prefix_{}'.format(i)] = prefix
        result_dic['predicted_scenario_{}'.format(i)] = predicted_scenario
        result_dic['match_{}'.format(i)] = match
        if match:
            acc_count += 1
    score = acc_count / test_cases
    result_dic['score'] = score
    return result_dic

##Realized this wont work because you have to start a new python session every time you make a new model.
#def conduct_test_across_checkpoints(checkpoint_list,n_objs, n_containers,sess,gpt2,
#    test_cases = 10, testing = False, temperature = 0.7):
#    results_dic = {}
#    for checkpoint in checkpoint_list:
#        result_dic = conduct_test(n_objs,n_containers,sess,gpt2,checkpoint,
#            test_cases=test_cases,testing_conts=testing, testing_nouns=testing, 
#            temperature=temperature)
#        print('Score for {}_objs_{}_containers at checkpoint {} = {}'.format(
#            n_objs, n_containers, checkpoint, result_dic['score']))
#        results_dic['{}_objs_{}_containers_{}_checkpoint'.format(n_objs,n_containers,checkpoint)] = result_dic
#    return results_dic

def score_dic_on_substrings(result_dic, n_containers, n_test_cases = 20):
    #There are multiple containers in each result_dic
    case_scores = []
    for i in range(n_test_cases):
        true_scenario = result_dic['true_scenario_{}'.format(i)]
        prefix = result_dic['prefix_{}'.format(i)]
        generated_scenario = result_dic['predicted_scenario_{}'.format(i)]
        true_fs = true_scenario.replace(prefix,'')
        true_fs_components = true_fs.split('.')[1:-1]
        generated_fs = generated_scenario.replace(prefix,'')
        score = 0.0
        for true_fs_component in true_fs_components:
            if true_fs_component in generated_fs:
            #    print(true_fs_component, ' is inside')
                score += 1
            #else:
            #    print(true_fs_component, ' is outside')
        score /= len(true_fs_components)
        case_scores.append(score)
        case_score_mean = np.mean(case_scores)
    return case_score_mean

def gather_scores_for_dics(n_objs_list, n_containers_list, experiment_name, n_test_cases, other='', testing = False):
    accuracies = np.ones((len(n_containers_list), len(n_objs_list))) * -1
    for i,n_objs in enumerate(n_objs_list):
        pickle_name = 'results/{}/results_dic_{}_nouns_{}_objects{}.p'.format(experiment_name,'test' if testing else 'train', n_objs,other)
        results_dic = load_pickle(pickle_name)
        for j,n_containers in enumerate(n_containers_list):
            key_name = '{}_objs_{}_containers'.format(n_objs,n_containers)
            result_dic = results_dic[key_name]
            score = score_dic_on_substrings(result_dic, n_containers,n_test_cases=n_test_cases)
            #print(score)
            accuracies[j,i] = score
    #print(accuracies)
    return accuracies


def score_pickle(pickle_name):
    result_dic = load_pickle(pickle_name)
    score = score_dic_on_substrings(result_dic, 19)
    return score

def load_pickle(pickle_name):
    """Loads a pickle"""
    result = pickle.load(open(pickle_name, 'rb'))
    return result

def dump_pickle(thing, pickle_name):
    """Dumps thing into pickle_name"""
    return pickle.dump(thing, open(pickle_name, 'wb'))

if __name__=="__main__":
    import gpt_2_simple as gpt2
    import time
    import numpy as np
    import pickle
    import argparse

    parser = argparse.ArgumentParser(description='Run gpt2 test suite')
    #TODO add option to give a list of objects and a list of containers
    #from command line maybe
    parser.add_argument('--n_objects', type=int)
    parser.add_argument('--n_containers', type=int)
    parser.add_argument('--test_cases', type=int)
    parser.add_argument('--step')
    parser.add_argument('--run_name')
    parser.add_argument('--testing', action='store_true')
    args = parser.parse_args()
    
    if args.n_objects:
        n_objects_list = [args.n_objects]
    else:
        n_objects_list = np.arange(1,19)

    if args.n_containers:
        n_containers_list = [args.n_containers]
    else:
        n_containers_list = np.arange(2,6)

    run_name = args.run_name
    testing = args.testing
    test_cases = args.test_cases
    step = args.step
    print('This is the step in the program ', step)
	
    sess = gpt2.start_tf_sess()
    gpt2.load_gpt2(sess,run_name=run_name, step=step)
    #results_dic = conduct_tests(n_objects, n_containers, sess, gpt2,\
    #    run_name, testing_conts=testing, testing_nouns = testing, 
    #    test_cases = test_cases)
    for n_objects in n_objects_list:
        for n_containers in n_containers_list:

            start = time.time()
            result_dic = conduct_test(
                n_objects,
                n_containers,
                sess,
                gpt2,
                run_name,
                step=step,
                testing_conts = testing,
                testing_nouns = testing,
                test_cases = test_cases)
            file_name = 'results_dic_{}_{}_objs_{}_containers_{}_{}.p'.format(
                'test' if testing else 'train',
                n_objects,
                n_containers,
                run_name,
                step)
            f = open(file_name, 'wb')
            pickle.dump(result_dic, f)
            f.close()
            print('Took {} seconds to test {} objects {} containers'.format(
                time.time() - start,
                n_objects,
                n_containers)
                )

