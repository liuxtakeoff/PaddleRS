#!/bin/bash

function func_parser_key() {
    strs=$1
    IFS=":"
    array=(${strs})
    tmp=${array[0]}
    echo ${tmp}
}

function func_parser_value() {
    strs=$1
    IFS=":"
    array=(${strs})
    tmp=${array[1]}
    echo ${tmp}
}

function func_parser_value_lite() {
    strs=$1
    IFS=$2
    array=(${strs})
    tmp=${array[1]}
    echo ${tmp}
}

function func_set_params() {
    key=$1
    value=$2
    if [ ${key}x = "null"x ];then
        echo " "
    elif [[ ${value} = "null" ]] || [[ ${value} = " " ]] || [ ${#value} -le 0 ];then
        echo " "
    else 
        echo "${key}=${value}"
    fi
}

function func_parser_params() {
    strs=$1
    IFS=":"
    array=(${strs})
    key=${array[0]}
    tmp=${array[1]}
    IFS="|"
    res=""
    for _params in ${tmp[*]}; do
        IFS="="
        array=(${_params})
        mode=${array[0]}
        value=${array[1]}
        if [[ ${mode} = ${MODE} ]]; then
            IFS="|"
            #echo $(func_set_params "${mode}" "${value}")
            echo $value
            break
        fi
        IFS="|"
    done
    echo ${res}
}

function status_check() {
    local last_status=$1   # the exit code
    local run_command=$2
    local run_log=$3
    local model_name=$4

    if [ $last_status -eq 0 ]; then
        echo -e "\033[33m Run successfully with command - ${model_name} - ${run_command}!  \033[0m" | tee -a ${run_log}
    else
        echo -e "\033[33m Run failed with command - ${model_name} - ${run_command}!  \033[0m" | tee -a ${run_log}
    fi
}

function download_and_unzip_dataset() {
    local ds_dir="$1"
    local ds_name="$2"
    local url="$3"
    local clear="${4-True}"

    local ds_path="${ds_dir}/${ds_name}"
    local zip_name="${url##*/}"

    if [ ${clear} = 'True' ]; then
        rm -rf "${ds_path}"
    fi

    wget -nc -P "${ds_dir}" "${url}" --no-check-certificate
    cd "${ds_dir}" && unzip "${zip_name}" && cd - \
        && echo "Successfully downloaded ${zip_name} from ${url}. File saved in ${ds_path}. "
}

function parse_extra_args() {
    local lines=("$@")
    local last_idx=$((${#lines[@]}-1))
    local IFS=';'
    extra_args=(${lines[last_idx]})
}

function add_suffix() {
    local ori_path="$1"
    local suffix=$2
    local ext="${ori_path##*.}"
    echo "${ori_path%.*}${suffix}.${ext}"
}

function parse_first_value() {
    local key_values=$1
    local IFS=":"
    local arr=(${key_values})
    echo ${arr[1]}
}

function parse_second_value() {
    local key_values=$1
    local IFS=":"
    local arr=(${key_values})
    echo ${arr[2]}
}

function run_command() {
    local cmd="$1"
    local log_path="$2"
    if [ -n "${log_path}" ]; then
        eval ${cmd} | tee "${log_path}"
        test ${PIPESTATUS[0]} -eq 0
    else
        eval ${cmd}
    fi
}
